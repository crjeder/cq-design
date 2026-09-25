## 1. Export script

- [x] 1.1 Add `src/export_standalone.py` (`--parts-dir build --out standalone [--parameters parameters.py]`): AST-scan each `<parts-dir>/*.py` (skip `build.py`) for imports of `cq_verify`, `cq_compat`, `blocks`; copy those from `src/`, repeating the scan over copied helpers until stable
- [x] 1.2 Write `<out>/pyproject.toml` (cadquery only; add `cq-warehouse` git source when a shipped `.py` mentions `cq_warehouse` or `heat_set_boss`) and copy `parameters.py` when present
- [x] 1.3 Write `<out>/README.md`: how to run each script, where `# PARAMETERS` lives, and any non-cadquery imports the scan could not resolve

## 2. Tests

- [x] 2.1 `tests/test_export_standalone.py`: cadquery-only part ships alone; part with `cq_verify` + `blocks` gets exactly those and no `mesh_io.py`/`exporters/`; `heat_set_boss` adds `cq-warehouse`; re-run overwrites
- [x] 2.2 One integration test running a shipped template script (`python <part>.py` from `<out>`) with cadquery

## 3. Docs and wiring

- [x] 3.1 `skill/phase4_deliver.md`: run the export as a delivery step, add `standalone/` to the output-files list and README layout
- [x] 3.2 `reference/scripts.md` and `CLAUDE.md` file layout: add `export_standalone.py`
- [x] 3.3 `src/skill_permissions.json`: allow `export_standalone.py` (Bash and PowerShell patterns, matching `bundle_project.py`)
- [x] 3.4 `TODO.md`: mark "A minimal deliverable for a parametric part" done
