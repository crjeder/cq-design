## Why

Once the skill finishes a run, the deliverable `build/` directory holds the per-part
scripts and the exported meshes, but nothing the user can re-run to rebuild the plates
themselves. After hand-editing a part script or tweaking a parameter, the user has to
re-invoke the whole skill (which needs Claude in the loop) just to regenerate
`model.3mf` and the per-plate STLs in print orientation. A self-contained `build.py`
dropped into `build/` makes plate regeneration a single `python build/build.py`,
independent of Claude.

## What Changes

- Add a `build.py` **template** under `src/` (the skill's source of truth). It is a
  runnable Python script that, when executed, regenerates every build plate with each
  object in its recommended **print orientation**.
- During Phase 3 (Build), the skill **copies** this template into the `build/`
  subdirectory of the current working directory, substituting the absolute skill `src`
  path so the copied script can import the shared tooling (`blocks`, `model_export`,
  `print_orientation`) without the skill being re-invoked.
- When run, `build/build.py` reads `BUILD_PLAN.json`, computes the print orientation per
  union (reusing `print_orientation.optimize_orientation`), and emits the deliverable
  `model.3mf`, per-union STLs, and fused per-plate STLs in print orientation (reusing
  `model_export.export_model`) — the same artifacts the skill produces, but reproducibly
  and on demand.
- The script prints a per-union summary (chosen orientation + output paths) and exits
  non-zero on failure so it is usable in scripts and CI.
- `SKILL.md` documents the copy step in Phase 3 and lists `build/build.py` among the
  Phase 4 deliverables.

## Capabilities

### New Capabilities
- `build-script`: a deliverable, self-contained `build.py` placed in the working
  directory's `build/` that regenerates all build plates with objects in print
  orientation, reusing the skill's export and orientation tooling.

### Modified Capabilities
<!-- None: model-export and print-orientation behavior is reused unchanged; build.py is a new orchestrating deliverable. -->

## Impact

- **New code**: `src/build_template.py` (the build.py template).
- **Reused unchanged**: `src/model_export.py` (`export_model`), `src/print_orientation.py`
  (`optimize_orientation`), `src/mesh_io.py` (`load_mesh`).
- **Pipeline / docs**: `SKILL.md` gains the template-copy step in Phase 3 and a
  `build/build.py` entry in Phase 4 deliverables; `CLAUDE.md` notes the new src file.
- **Dependencies**: none new (trimesh + numpy + CadQuery already required).
