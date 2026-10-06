## 1. Split and rename

- [x] 1.1 `git mv src/model_export.py src/write_assembly.py`; rename `export_model` -> `write_assembly`, `_pose_union` -> `pose_union`; drop 3MF, plate, extra-format and `formats` code; return `union_stls`, `keep_out_stls`, `manifest`, `pose_findings`; progress lines per part and per union STL only
- [x] 1.2 Create `src/deliverables.py` with `write_deliverables(plan, parts_dir, out, orientations, formats, progress)` and the moved 3MF naming helpers (`_object_name`, `_dedupe_object_names`), reusing `load_part_unions`/`pose_union` from `write_assembly`
- [x] 1.3 Update importers: `bundle_project.py` (bundle list), `init_permissions.py`, `skill_permissions.json`, `keep_out_check.py`, `kinematic_check.py`, `minimal_cutout_search.py`, `plate_clearance_check.py`, `print_finishing.py`, `units.py`, `evals/run_evals.py`; `rg "model_export|export_model"` finds nothing outside archived changes

## 2. build.py

- [x] 2.1 `src/build_template.py`: `--formats` (default preferred_format; accepts `3mf,stl,step,obj,iges,scad`), single `--out` default `<root>/out`, remove `--stl-out`; call `write_deliverables`; summary lists files per format
- [x] 2.2 Copy-when-fresh for per-union STLs from `<root>/stl` (manifest, `stale_ids`, `pose_stale_ids`, file existence; skip same dir); report copied vs regenerated
- [x] 2.3 Update the template docstring (arguments, outputs, `out/` vs `stl/`)

## 3. Command

- [x] 3.1 Add `commands/build.md` (`/cq-design:build [format]`, missing-`build/build.py` guard); delete `commands/deliver.md`; update command lists (`README.md`, `FILES.md`, `CLAUDE.md`, `.claude-plugin`/`SKILL.md` if listed)

## 4. Skill flow and docs

- [x] 4.1 `skill/phase3_build.md`: Model export step becomes `write_assembly.py` -> gate -> bundle -> `uv sync` -> `build/build.py`; `skill/phase4_deliver.md`: list `out/` files and layout; `skill/resume.md`: same refresh instructions
- [x] 4.2 `README.md`, `FILES.md`, `reference/scripts.md`, `CLAUDE.md`, `TODO.md`, and specs that name `model_export.py` (`assembly-phase`, `assembled-pose-handback`, `part-copies`, `minimal-cutout-search`, `file-error-reporting`, `self-contained-build-environment`) updated to `write_assembly.py`

## 5. Tests

- [x] 5.1 Rename `tests/test_model_export.py` -> `tests/test_assembly_and_deliverables.py` (one file: write_assembly + deliverables); add "only requested files written" and copy-when-fresh cases
- [x] 5.2 `tests/test_build_script.py`: default preferred-only, multiple formats, unsupported key, `--stl-out` rejected, fresh copy vs stale regenerate; fix `test_keep_out_check.py`, `test_input_errors.py`, `test_print_finishing.py` imports
- [x] 5.3 Run `uv run pytest tests/` and `openspec validate build-copies-delivered-stl`
