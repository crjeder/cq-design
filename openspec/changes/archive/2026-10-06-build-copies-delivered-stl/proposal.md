## Why

`model_export.py` (run by the skill) and the bundled `build/build.py` both call `export_model`
and write the same files: `model.3mf`, per-union STLs, plate STLs, extra formats. The two
write to different places and duplicate each other's CadQuery work, and the skill's export
produces formats nobody asked for. Two jobs are tangled in one module: (1) the assembled-pose
STLs + provenance manifest the whole-model checks need, and (2) the user-facing model files.

## What Changes

- `build.py` becomes the only generator of user-facing model files. `--formats LIST`
  (`3mf`, `stl`, `step`, `obj`, `iges`, `scad`) selects what to write; with no `--formats` it
  writes only the profile's `slicer.preferred_format`. Everything lands in one `--out`
  directory (default `<root>/out`).
- **BREAKING**: `--stl-out` is removed. `--formats` now also accepts `3mf` and `stl`.
- The skill's last phase runs `build.py` (after bundling) to produce the user's files; a manual
  `build.py --formats ...` or `/cq-design:build <format>` regenerates any format later.
- `model_export.py` is renamed `write_assembly.py`, `export_model` -> `write_assembly`. It now
  writes only what the checks consume: assembled-pose per-union STLs, keep-out-zone STLs and
  the provenance manifest into `stl/`. It no longer writes `model.3mf`, plate STLs or extra
  formats. The 3MF/plate/extra writers move to a new `deliverables.py` used by `build.py`.
- When `stl` is requested and the manifest shows the last-phase per-union STLs in `stl/` are
  current, `build.py` copies them instead of regenerating.
- **BREAKING**: `/cq-design:deliver` is removed; `/cq-design:build [format]` replaces it.
  (`run_cadquery_model.py --deliver` stays: the part loop uses it.)

## Capabilities

### New Capabilities
- `build-command`: `/cq-design:build [format]` runs the project's `build/build.py`.

### Modified Capabilities
- `build-script`: `--formats` selects formats (default preferred), single `--out`, copy-when-fresh.
- `model-export`: module renamed to `write_assembly`; scope reduced to assembled-pose STLs,
  keep-out STLs and manifest. 3MF, plate and extra-format requirements move to `build-script`.

## Impact

- `src/model_export.py` -> `src/write_assembly.py`; new `src/deliverables.py`;
  `src/build_template.py`; importers: `bundle_project.py`, `init_permissions.py`,
  `skill_permissions.json`, `keep_out_check.py`, `kinematic_check.py`,
  `minimal_cutout_search.py`, `plate_clearance_check.py`, `print_finishing.py`, `units.py`,
  `evals/run_evals.py`.
- `commands/deliver.md` removed, `commands/build.md` added; plugin command list in docs and
  the (unarchived) `package-skill-as-plugin` plugin-commands spec.
- Tests: `tests/test_model_export.py` (renamed/split), `test_build_script.py`,
  `test_keep_out_check.py`, `test_input_errors.py`, `test_print_finishing.py`.
- Docs: `skill/phase3_build.md`, `skill/phase4_deliver.md`, `skill/resume.md`, `README.md`,
  `FILES.md`, `reference/scripts.md`, `CLAUDE.md`, `TODO.md`; specs naming `model_export.py`
  (`assembly-phase`, `assembled-pose-handback`, `part-copies`, others).
- Existing projects: `/cq-design:update` refreshes `lib/` and `build/build.py`; scripts passing
  `--stl-out` must drop it; model files move from project root to `out/`.
