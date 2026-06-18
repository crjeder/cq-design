## Context

The existing skill is a single SKILL.md document Claude reads and follows as a long iterative loop: write CadQuery script, run wrapper, inspect preview image, fix errors, repeat. The wrapper (`run_cadquery_model.py`) runs the script as a subprocess, discovers output STLs by mtime, checks watertightness, optionally renders a 6-view PNG, and emits a JSON result. Errors surface as raw OCC tracebacks in `stderr`. Geometry facts (bounding box, volume) are rendered into preview image footers but not available as structured data. There is no planning phase, no reusable primitive library, and no distinction between iteration artifacts and deliverable artifacts.

The redesign introduces a four-phase architecture: plan → build parts → assemble → quality gate. Python drives the loop; LLM calls are scoped to specific, context-bounded tasks.

## Goals / Non-Goals

**Goals:**
- Structured `BUILD_PLAN.json` produced before any code runs, editable by user before loop starts
- Building blocks library with machine-readable inventory enabling short, focused per-part prompts
- Python orchestrates the part loop — reads plan, invokes `claude -p`, validates, retries — without LLM involvement in loop control
- Wrapper emits structured errors with face/edge IDs, gap measurements, and hints; never raw OCC tracebacks
- Wrapper emits geometry metrics (`bbox`, `volume_cm3`, `weight_g`, `face_count`) in JSON
- STL is an internal temp artifact during iteration; LLM works in code space only
- All deliverable formats (STL, 3MF, STEP, OBJ) derived from the final CadQuery result at export time
- OpenSCAD MCP/skill replaced: this skill becomes the single 3D-printing skill

**Non-Goals:**
- GUI or web interface
- Multi-user / cloud execution
- Support for CAD formats other than CadQuery Python as the canonical model format
- Real-time collaboration on models
- Native SCAD code generation (SCAD output is mesh-based fallback only: `import("model.stl")`)
- FreeCAD parametric output (may be added later as an exporter)

## Decisions

### D1: BUILD_PLAN.json as a plain JSON file, not an OpenSpec artifact

**Decision:** The planning output is a `BUILD_PLAN.json` file on disk, shown to the user for review and editable before the build loop starts.

**Rationale:** The plan is session-scoped scaffolding, not a persistent design specification. OpenSpec adds approval workflow overhead that is not needed here. A JSON file is directly machine-parseable by the Python orchestrator without any additional tooling. The user can edit it in any text editor.

**Alternative considered:** OpenSpec change artifact. Rejected because it adds ceremony (separate approval step, schema validation) without quality benefit for a within-session artifact.

---

### D2: Python orchestrates the part loop via `claude -p`

**Decision:** The Python orchestrator (`orchestrate.py`) reads `BUILD_PLAN.json`, renders per-part prompt files, calls `claude -p <prompt_file>` as a subprocess, collects the generated code, runs the wrapper, and retries on failure — all without LLM involvement in loop control.

**Rationale:** Deterministic loop control. Python can enforce retry limits, validate dimensions against the plan, format structured correction prompts, and stop on unrecoverable errors without the loop itself being subject to LLM variability. The LLM is called only for code generation, not for deciding what to do next.

**Alternative considered:** Claude as orchestrator using tool calls. Rejected because loop control becomes LLM-dependent; retry decisions, dimension checking, and error routing all require the LLM to be correct about mechanical tasks it can fail silently on.

---

### D3: Temp-dir STL strategy — no STL surfaces to LLM during iteration

**Decision:** The wrapper exports to a per-run temp directory. It analyzes the temp STL for geometry facts and topology errors. The STL path is not included in the JSON returned to the LLM. The LLM works in code space throughout iteration. The output phase reads the final approved code and re-exports to the user's requested formats.

**Rationale:** Keeps the LLM's mental model clean: it is always editing Python code, not managing file artifacts. Avoids the conceptual confusion where the LLM thinks "I produced a good STL" and stops iterating even though the geometry is wrong. Re-running export at delivery time also ensures all output formats are derived from the same final code, with no stale-cache risk.

**Alternative considered:** Report STL path in JSON as currently done. Rejected because it mixes work artifacts with deliverable artifacts and encourages the LLM to treat the STL as done before the quality gate.

---

### D4: Structured errors from topology analysis, not traceback parsing

**Decision:** After running the model script, the wrapper performs topology analysis using CadQuery's OCC bindings and trimesh. It maps known failure patterns to structured error objects with `type`, `location` (face/edge hash), `gap_mm` or `delta_mm`, and `hint`. Raw OCC tracebacks are still captured in `stderr` for debugging but are not the primary error channel.

**Known error types to detect:**
- `non_manifold_edge`: trimesh identifies non-manifold edges with face adjacency
- `dimension_mismatch`: compare `result.val().BoundingBox()` against plan spec
- `no_geometry`: script exited 0 but produced no CadQuery result
- `boolean_gap`: volume of result significantly less than expected (boolean left a gap)
- `thin_wall`: minimum wall thickness below `constraints.wall_min_mm`
- `occ_exception`: untranslated OCC exception — include class name and message, strip stack frames

**Rationale:** Structured errors let the LLM fix precisely rather than guess. A hint like "extend inner body 0.01mm past outer boundary to close boolean gap at edge e-a3f2" is actionable in one retry. A raw `BRep_API: command not done` traceback requires the LLM to know OCC internals.

---

### D5: Block inventory as `blocks/inventory.json`

**Decision:** Each block is described in `inventory.json` with `name`, `module`, `function`, `use` (plain English description), `params` (name → unit), `dimensions` (typical bounding box in mm), and `interfaces` (list of `{type, orientation, origin}`).

**Interface type vocabulary (closed set):**

| type | meaning |
|------|---------|
| `face_mount` | flat face bonded/fastened to a wall or surface |
| `screw_hole` | threaded or clearance hole; axis along orientation |
| `snap_hook` | cantilever clip that deflects and locks |
| `snap_socket` | receiver pocket for a snap_hook |
| `axis` | rotational axis (hinges, pivots) |
| `pin` | alignment/press-fit post |
| `socket` | alignment/press-fit receiver for a pin |
| `slot` | elongated opening (cable, connector passage) |
| `port_cutout` | negative space for a standard connector |

**Rationale:** A closed vocabulary enables Python to validate interface compatibility at assembly time (a `snap_hook` mates with a `snap_socket`; a `pin` mates with a `socket`). Plain text `use` descriptions are included verbatim in per-part prompts, keeping LLM context minimal while giving enough information to select correctly.

**Alternative considered:** Embed block documentation in SKILL.md as code snippets. Rejected because it cannot be queried programmatically, grows unbounded, and forces the full library into every prompt's context.

---

### D6: Modular exporter — output derived from CadQuery result, not STL

**Decision:** `exporters/__init__.py` exposes `run_exporters(script_path, formats, output_dir)`, which imports the model script, extracts the `result` variable, and calls the appropriate exporter for each requested format.

**Format support:**
- `stl`: `cq.exporters.export(result, path)` — native
- `step`: `cq.exporters.export(result, path)` — native
- `3mf`: trimesh conversion from in-memory mesh — carried over from `stl_to_3mf.py`
- `obj`: trimesh conversion from in-memory mesh
- `iges`: `cq.exporters.export(result, path)` — native
- `scad`: mesh-based fallback — export STL to temp, write `import("model.stl");` wrapper

**Rationale:** All formats from the same source means no stale-cache divergence. Adding a new format is one new file in `exporters/`. SCAD is included as mesh-based fallback to replace the existing OpenSCAD skill without losing the ability to hand off to OpenSCAD tooling.

---

### D7: Per-phase prompt files under `prompts/`

**Decision:** `prompts/planning.md`, `prompts/part.md`, `prompts/assembly.md` replace the monolithic SKILL.md guidance. Each is invoked with only the context it needs. `SKILL.md` becomes a thin orchestration guide.

**Planning prompt** (~400 tokens): system role + JSON output schema for `BUILD_PLAN`. Embeds condensed block inventory (name + use only, not full params). Instructs web search for real-world dimensions.

**Part prompt** (~300 tokens + part spec): role = "write ONE CadQuery part"; includes only the blocks needed for this part (from `blocks_needed` in plan); includes the part's interface and dimension spec; outputs Python code only.

**Assembly prompt** (~300 tokens + verified dims): role = "combine these verified parts"; receives actual bounding box dimensions from wrapper JSON (not the plan's estimates); outputs assembly Python code.

**Rationale:** Short focused prompts reduce hallucination surface area and token cost. The LLM for part generation has no knowledge of other parts — it cannot accidentally reference them or create geometry that assumes they exist.

## Risks / Trade-offs

**`claude -p` subprocess coupling** → The orchestrator assumes `claude` CLI is in PATH. If the CLI is unavailable or the API is unreachable, the entire loop fails. Mitigation: orchestrator checks `claude --version` at startup and fails fast with a clear error.

**Model script `result` variable convention** → The exporter imports the model script and expects a top-level `result` variable. Scripts that use different names or build result inside functions will break. Mitigation: SKILL.md and part prompt enforce this convention explicitly; wrapper validates the variable exists after import.

**Topology analysis latency** → Running OCC topology analysis on every iteration adds 0.5-2s per run. Mitigation: topology analysis only runs when the script succeeds; it is skipped on OCC exceptions (error is already known). The cost is acceptable given the retry-loop savings from precise errors.

**OCC exception coverage** → Not all OCC errors map to a known structured type. Unknown exceptions fall back to `occ_exception` with the class name and message. This is better than a raw traceback but less actionable than a typed error. Mitigation: extend the translator incrementally as new error patterns are encountered in practice.

**SCAD output is not parametric** → `scad` export wraps an STL import, which is not editable in OpenSCAD as a parametric model. This is a regression vs. a native SCAD skill. Mitigation: document the limitation clearly; the CadQuery `.py` source is the parametric form.

## Open Questions

- **`BUILD_PLAN.json` schema version field**: should the schema include a `version` field for forward compatibility as the block vocabulary evolves? Lean yes — add `"schema_version": 1`.
- **Retry limit for part loop**: 3 retries per part seems right, but should the orchestrator ask the user to intervene after exhausting retries, or fail the whole build? Lean toward user intervention with a clear error summary.
- **Assembly validation depth**: the assembly phase should check that no parts interpenetrate. CadQuery's `intersect()` can detect this but is slow on complex geometry. Worth doing or skip for v2? Lean toward skip for v2, document as known gap.
