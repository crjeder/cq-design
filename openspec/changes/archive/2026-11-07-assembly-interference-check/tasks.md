## 1. Plan schema and resolver

- [x] 1.1 Add optional `union` to `joints[].members[]` in `src/build_plan_schema.json`
- [x] 1.2 Add `member_union(part, member)` / `part_union_ids(part)` resolvers in `src/units.py` (default to the single union)
- [x] 1.3 Validate in `src/plan.py`: required for multi-union parts, must exist in the part; test in `tests/test_plan.py`
- [x] 1.4 Switch `_is_hinge_associated_union` in `src/quality_gate.py` to the resolver

## 2. Check

- [x] 2.1 Add `src/assembly_interference_check.py` (`run_assembly_interference_check`, CLI via `run_stl_dir_check_cli`): fcl internal collision, skip co-plated and press-fit pairs (negative declared clearance, copies inherit), epsilon 0.1 mm^3, `assembly_interference` error with `union_a`, `union_b`, `overlap_mm3`
- [x] 2.2 Staleness, missing-STL and missing-backend degrade paths matching `keep_out_check`
- [x] 2.3 Tests: sunk lid fails, flush passes, co-plated skipped, press-fit exempt, positive-clearance not exempt, copy exempt

## 3. Wiring and docs

- [x] 3.1 Add the stage to `quality_gate.py` after the keep-out stage
- [x] 3.2 Update `reference/scripts.md`, `FILES.md`, and the `interference.py` docstring (second caller)
- [x] 3.3 Run `uv run pytest tests/` and `ruff check` / `ruff format`
