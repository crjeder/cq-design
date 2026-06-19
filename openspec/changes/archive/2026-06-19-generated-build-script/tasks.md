## 1. Build script template

- [x] 1.1 Create `src/build_template.py` with a `SKILL_SRC = "{{SKILL_SRC}}"` placeholder and a `sys.path` insert before importing `model_export`, `print_orientation`, `mesh_io`
- [x] 1.2 Implement argparse with `--plan`, `--parts-dir`, `--out` defaulting to `<script_dir>/../BUILD_PLAN.json`, `<script_dir>`, and `<script_dir>` so a no-arg `python build/build.py` works
- [x] 1.3 Load each union's authored mesh and call `optimize_orientation` with the part's `load` hint and the plan's `overhang_max_deg`, building the `{part_id: {"rotate": [...]}}` map
- [x] 1.4 Call `export_model(plan, parts_dir, out, print_orientations)` to regenerate `model.3mf`, per-union STLs, and fused per-plate STLs in print orientation
- [x] 1.5 Print a per-union summary (chosen orientation + output paths); exit non-zero naming the failing union on load/orient/export failure, including a clear message when `SKILL_SRC` does not exist

## 2. Skill integration

- [x] 2.1 Add a Phase 3 step in `SKILL.md` that copies `src/build_template.py` to `build/build.py`, substituting `{{SKILL_SRC}}` with the absolute skill `src/` path
- [x] 2.2 List `build/build.py` among the Phase 4 deliverables in `SKILL.md`
- [x] 2.3 Add `src/build_template.py` to the Core Scripts / File Layout tables in `CLAUDE.md`

## 3. Tests

- [x] 3.1 Add `tests/test_build_script.py`: copy the template with `SKILL_SRC` substituted to the test src, run the resulting `build.py` against a fixture plan + part scripts, assert `model.3mf` and per-union/per-plate STLs are written
- [x] 3.2 Assert exit code is non-zero and names the union when a part script is missing or unloadable
- [x] 3.3 Assert orientation is applied (deliverable bbox differs from the authored pose for a part whose optimal orientation is a rotation) and is deterministic across two runs

## 4. Verification

- [x] 4.1 Run `uv run pytest tests/test_build_script.py` and confirm green
- [x] 4.2 Run `ruff check --fix` and `ruff format` on `src/build_template.py` and the new test
