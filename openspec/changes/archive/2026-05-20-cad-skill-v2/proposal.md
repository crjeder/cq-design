## Why

The current parametric-3d-printing skill works as one monolithic loop: Claude writes CadQuery code, runs it, stares at a preview image, and iterates. This produces fragile, token-heavy sessions where geometry errors are opaque, planning happens inline (if at all), and every iteration re-explains the entire design to the LLM. For anything beyond a simple box, this breaks down quickly.

## What Changes

- **NEW** Structured planning phase generates a machine-readable `BUILD_PLAN.json` before any code is written, decomposing the model into parts, physical interfaces, and required building blocks
- **NEW** Building blocks library (`blocks/`) provides parametric primitives with a machine-readable inventory (`blocks/inventory.json`) declaring name, use-case, dimensions, and typed interfaces
- **NEW** Python orchestration loop reads `BUILD_PLAN.json` and drives one focused LLM call per part, rather than one giant session-spanning conversation
- **NEW** Structured error feedback — the wrapper performs topology analysis and emits specific face/edge IDs, gap measurements, and actionable hints instead of raw OCC tracebacks
- **NEW** Geometry metrics in wrapper JSON output (`bbox`, `volume_cm3`, `weight_g`, `face_count`) so Claude never needs to read image footers for dimensional facts
- **NEW** Modular exporter (`exporters/`) derives all output formats from the final CadQuery result object — no cached STL as source of truth; STL, 3MF, STEP, OBJ supported; SCAD as mesh-based fallback
- **MODIFIED** `run_cadquery_model.py` — temp-dir STL strategy: internal geometry analysis uses a temporary STL; no STL is surfaced to the LLM as a work artifact during iteration
- **MODIFIED** `SKILL.md` — thinned to phase orchestration instructions; implementation details moved to per-phase prompt files under `prompts/`
- **REMOVED** `stl_to_3mf.py` as standalone script — absorbed into `exporters/threemf.py`

## Capabilities

### New Capabilities

- `planning-phase`: Structured upfront planning — user intent, physical interfaces, dimension research, part decomposition, block selection — producing a validated `BUILD_PLAN.json` before any code runs
- `block-library`: Parametric building-block primitives with machine-readable inventory (name, use-case, bounding box, typed interface declarations) enabling short focused part prompts and Python-level interface validation
- `orchestration-loop`: Python-driven per-part build loop that reads `BUILD_PLAN.json`, invokes focused LLM calls, runs the wrapper, checks geometry against plan, and retries with structured corrections
- `structured-errors`: Topology-aware error reporting in wrapper JSON — face/edge IDs, gap measurements, dimension deltas, and per-error actionable hints derived without LLM involvement
- `modular-exporters`: Format-pluggable output layer that derives all deliverable formats from the final CadQuery result object at export time

### Modified Capabilities

- `preview-and-validate`: Wrapper now emits geometry metrics (`bbox`, `volume_cm3`, `weight_g`, `face_count`) in the JSON contract alongside the existing watertight flag; STL is produced in a temp dir and not returned to the LLM as a work artifact

## Impact

- `run_cadquery_model.py` — significant expansion: temp-STL strategy, topology analysis, structured error emission, geometry metrics
- `SKILL.md` — stripped down; `prompts/planning.md`, `prompts/part.md`, `prompts/assembly.md` added
- `stl_to_3mf.py` — replaced by `exporters/threemf.py`
- `requirements.txt` — no new top-level dependencies expected; topology analysis uses CadQuery's existing OCC bindings and trimesh
- `preview.py`, `mesh_io.py` — unchanged
- `tests/` — existing tests remain valid; new tests needed for orchestrator, block inventory, exporters, and error translator
