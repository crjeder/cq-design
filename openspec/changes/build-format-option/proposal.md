## Why

`build.py` is the one-command way to regenerate a finished project, but it writes only `model.3mf` and STLs. A STEP file (or any other format the exporters support) needs a separate `run_cadquery_model.py --deliver --formats step` run per part script, and that run produces the authored pose, not the assembled pose `build.py` uses for the STLs.

## What Changes

- `build.py` gains `--formats LIST`: comma-separated extra formats (`step`, `obj`, `iges`, `scad`) written in addition to the always-written 3MF and STLs. Default: none.
- `model_export.py` gains the same `--formats` option and an `export_model(..., formats=...)` parameter.
- Each extra format is written once per union as `<union-id>.<ext>`, in the assembled pose (same pose as the per-union STLs), using the existing modular exporters.
- `model.3mf`, the per-union STLs and the fused `plate_<n>.stl` are unchanged and always written (the kinematic, plate-clearance and keep-out checks consume the STLs).
- The result dict gains the per-union paths for the extra formats.
- No breaking changes: omitting `--formats` yields exactly the current output.

## Capabilities

### New Capabilities

### Modified Capabilities
- `build-script`: `build.py` accepts a `--formats` option and writes the requested formats.
- `model-export`: model-level export writes per-union files in additional formats in the assembled pose.

## Impact

- Code: `src/build_template.py`, `src/model_export.py`; reuses `src/exporters/`.
- Docs: README command-line reference, `reference/scripts.md`, `CLAUDE.md` if it lists build.py outputs.
- Tests: `tests/test_build_script.py`, `tests/test_model_export.py`.
- No new dependencies.
