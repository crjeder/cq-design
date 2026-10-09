## Why

The cq scripts juggle three poses: the **build pose** (the frame a part script is authored in, and the frame every user-facing direction -- `load.dir`, `show_face`, "top", "front" -- is expressed in), the **assembly pose** (the union's `placement` in the assembled model), and the **optimized print pose** (build pose rotated by the accepted `orientations.json`). Today only `model.3mf` and multi-union `plate_<n>.stl` are delivered in print pose; per-union `<union>.stl` and `step`/`obj`/`iges`/`scad` come out in the assembly pose, so a user who asks for an STL gets a file that is not ready to slice. The pose of each deliverable is also undocumented, and nothing states that user directions are build pose.

## What Changes

- All three poses are kept: scripts stay authored in build pose, `write_assembly.py` still writes assembly-pose meshes for the whole-model checks, and the accepted print rotation is still computed and stored.
- Every file the user requests from `build.py` (`3mf`, `stl`, `step`, `obj`, `iges`, `scad`) is delivered in print pose. A union without an accepted orientation is delivered in build pose (identity rotation), not assembly pose.
- Per-union `<union>.stl` is no longer copied from the assembly directory (that copy is assembly pose); it is exported from the build-pose geometry rotated into print pose.
- Document the three poses and the rule that every direction in conversation, plan, and CLI flags (`--load`, `--show-face`, `load.dir`) is build pose; only `orientations.json` `rotate` maps build -> print.
- **BREAKING**: `<union>.stl`, `.step`, `.obj`, `.iges`, `.scad` written by `build.py` change from assembly pose to print pose. Consumers needing assembly pose use the `write_assembly.py` output directory.

## Capabilities

### New Capabilities

### Modified Capabilities
- `build-script`: requested formats are all delivered in print pose; build-pose direction convention stated.
- `model-export`: assembly-pose meshes remain the checks' source of truth and are never altered or used as deliverables.

## Impact

- `src/deliverables.py` (`write_deliverables`, `_write_3mf`, `assembly_fresh` use), `src/build_template.py` (summary text).
- `reference/scripts.md`, `skill/phase3_build.md`, `skill/phase4_deliver.md`, `CLAUDE.md` pose glossary.
- Tests: `tests/test_exporters.py` and any `deliverables`/build template tests asserting STL/STEP pose.
