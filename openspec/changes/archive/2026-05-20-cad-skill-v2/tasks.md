## 1. Block Library

- [x] 1.1 Define `blocks/inventory.json` schema (name, module, function, use, params, dimensions, interfaces) with `schema_version: 1`
- [x] 1.2 Write `blocks/primitives.py`: `fillet_box`, `hollow_box`
- [x] 1.3 Write `blocks/fasteners.py`: `screw_boss`, `pcb_standoff`, `snap_hook_clip`, `snap_socket_receiver`, `alignment_pin`, `alignment_socket`
- [x] 1.4 Write `blocks/connectors.py`: `port_cutout`, `cable_slot`, `vent_grid`
- [x] 1.5 Populate `blocks/inventory.json` with all 11 initial blocks (correct params, dimensions, interfaces)
- [x] 1.6 Write `blocks/__init__.py` exposing all blocks via `from blocks import <name>`
- [x] 1.7 Write `tests/test_blocks.py`: import each block, call with valid params, assert returns CadQuery Workplane
- [x] 1.8 Write `blocks/validate.py`: load and validate `inventory.json` against schema; check interface types against closed vocabulary

## 2. Wrapper Expansion

- [x] 2.1 Add `geometry` field to wrapper JSON: `bbox` (x/y/z mm), `volume_cm3`, `weight_g`, `face_count`
- [x] 2.2 Add `errors: []` field to wrapper JSON (always present, empty on clean success)
- [x] 2.3 Implement temp-dir STL strategy: export to `tempfile.mkdtemp()` during iteration; set `stl: null`, `stls: []` in output
- [x] 2.4 Add `--deliver --formats <csv>` flags that invoke the modular exporter and populate `stl`/`stls`
- [x] 2.5 Implement OCC exception translator: map `Standard_ConstructionError`, `BRep_API`, `StdFail_NotDone`, `Standard_NullObject` to typed hints; unknown exceptions fall back to `occ_exception`
- [x] 2.6 Implement topology analysis: use trimesh to detect non-manifold edges, report each with face hash IDs and `gap_mm`
- [x] 2.7 Implement thin-wall DFM check: estimate minimum wall from face-pair proximity; emit `thin_wall` error if below `wall_min_mm`
- [x] 2.8 Accept optional `--expected-dims w,d,h` flag; emit `dimension_mismatch` errors for axes outside tolerance
- [x] 2.9 Update tests in `test_run_wrapper.py` to assert `geometry` and `errors` fields present in all JSON outputs
- [x] 2.10 Verify existing tests (`test_happy_path`, exit codes, timeout) still pass after changes

## 3. Modular Exporters

- [x] 3.1 Create `exporters/__init__.py` with `run_exporters(script_path, formats, output_dir)` and format registry
- [x] 3.2 Write `exporters/stl.py`: `export(result, path)` via `cq.exporters.export`
- [x] 3.3 Write `exporters/step.py`: `export(result, path)` via `cq.exporters.export`
- [x] 3.4 Write `exporters/threemf.py`: port `stl_to_3mf.py` logic to `export(result, path)` using trimesh
- [x] 3.5 Write `exporters/obj.py`: `export(result, path)` via trimesh in-memory conversion
- [x] 3.6 Write `exporters/iges.py`: `export(result, path)` via `cq.exporters.export`
- [x] 3.7 Write `exporters/scad.py`: export temp STL, write `import("model.stl");` wrapper with limitation comment
- [x] 3.8 Remove `stl_to_3mf.py` (functionality now in `exporters/threemf.py`)
- [x] 3.9 Write `tests/test_exporters.py`: for each format, run exporter against a known-good model script, assert output file exists and is non-empty

## 4. Planning Phase

- [x] 4.1 Write `BUILD_PLAN.json` JSON Schema (draft-7) covering all required fields from spec
- [x] 4.2 Write `plan_validate.py`: load and validate `BUILD_PLAN.json` against schema; report per-field errors
- [x] 4.3 Write `prompts/planning.md`: structured planning prompt producing `BUILD_PLAN.json` directly; embed condensed inventory (name + use only); include web-search instruction for real-world dimensions
- [x] 4.4 Write `tests/test_plan_validate.py`: valid plan passes; missing `dimensions`; unknown block name; empty parts array all fail with descriptive errors

## 5. Orchestration Loop

- [x] 5.1 Write `orchestrate.py` entry point: parse args (`--plan`, `--max-retries`, `--output-dir`), check `claude --version`, load and validate plan
- [x] 5.2 Implement per-part prompt renderer: read `prompts/part.md`, inject part spec and relevant block descriptors
- [x] 5.3 Implement `claude -p` subprocess call: write rendered prompt to temp file, invoke `claude -p <file>`, capture generated Python code
- [x] 5.4 Implement retry loop: run wrapper, check `errors` and `geometry`, build structured correction prompt on failure, enforce `--max-retries` limit
- [x] 5.5 Implement dimension validation: compare wrapper `geometry.bbox` against plan `dimensions`; build `dimension_mismatch` correction prompt if outside tolerance
- [x] 5.6 Implement user intervention prompt on retry exhaustion: display last error summary, offer skip/abort/hint options
- [x] 5.7 Implement `build_log.json` writer: incremental write after each part (not only at end)
- [x] 5.8 Write `prompts/part.md`: focused per-part prompt (~300 tokens base); role, block injection point, interface spec injection point, output-Python-only instruction
- [x] 5.9 Write `prompts/assembly.md`: focused assembly prompt; receives verified actual dimensions from wrapper JSON; outputs assembly Python code only
- [x] 5.10 Implement assembly phase: collect verified part files, render assembly prompt with actual dims, invoke `claude -p`, run wrapper on assembly result
- [x] 5.11 Write `tests/test_orchestrate.py`: mock `claude -p` responses; verify retry logic, build log format, dimension tolerance check

## 6. Quality Gate

- [x] 6.1 Write `quality_gate.py`: accepts final assembly script path and `BUILD_PLAN.json`; runs scad-analyzer MCP, orca-check MCP, and wrapper DFM checks
- [x] 6.2 Implement issue aggregation: collect all findings into a structured report with severity (`error`/`warning`) and per-issue `hint`
- [x] 6.3 Implement targeted fix prompt: if issues found, render a concise prompt with only the failing checks; invoke `claude -p`; re-run gate (max 2 rounds)
- [x] 6.4 Implement print recipe emission: on clean gate pass, output final slicer settings (material, layer height, walls, infill, supports, orientation)
- [x] 6.5 Integrate quality gate into `orchestrate.py` as the final phase after assembly

## 7. SKILL.md and Prompts Cleanup

- [x] 7.1 Thin `SKILL.md` to phase descriptions only: Planning, Part Loop, Assembly, Quality Gate — remove inline CadQuery patterns (these move to `prompts/part.md` and block docstrings)
- [x] 7.2 Update `SKILL.md` trigger description if needed
- [x] 7.3 Update `design-review.md` to reference new structured error output instead of manual checklist steps
- [x] 7.4 Update `CLAUDE.md` (skill dev) to reflect new file layout and test commands

## 8. Tests and Validation

- [x] 8.1 Run full test suite (`pytest tests/`) and confirm all existing tests pass — 75/75 passing
- [ ] 8.2 End-to-end smoke test: run `orchestrate.py` with a simple single-part plan (fillet box), confirm `build_log.json` and final preview produced (requires live `claude` CLI — manual)
- [ ] 8.3 End-to-end smoke test: run `orchestrate.py` with a two-part plan (body + lid), confirm assembly script produced (requires live `claude` CLI — manual)
- [x] 8.4 Confirm `python -c "from blocks.fasteners import pcb_standoff; print(pcb_standoff(2.5, 5, 4))"` produces a CadQuery result — verified
- [x] 8.5 Confirm `run_exporters(...)` produces three files — covered by `test_multiple_formats` (stl, step, 3mf all pass)
