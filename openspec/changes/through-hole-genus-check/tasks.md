## 1. Plan schema

- [ ] 1.1 Add optional `through_count` (integer, minimum 0, with description) to `parts[].interfaces[]` items in `src/build_plan_schema.json`
- [ ] 1.2 Add a `tests/test_plan.py` case: `through_count: 0`/`3` validate, `-1` and `1.5` fail

## 2. Mesh genus

- [ ] 2.1 Add `genus(mesh) -> int` to `src/mesh_io.py`: `c - euler_number // 2` with `c = len(mesh.split(only_watertight=False))`
- [ ] 2.2 Add `tests/test_mesh_io.py` cases: box -> 0, box with 3 through holes -> 3, box with 2 blind holes -> 0, box with internal void -> 0, two separate rings -> 2

## 3. Gate check

- [ ] 3.1 In `src/quality_gate.py` `run_gate` geometry stage, when the part has any interface with `through_count`, sum `mesh_io.genus` over the non-sacrificial union STLs (skip when any is not watertight) and emit a `through_hole_count_mismatch` error with `planned_b1`/`built_b1` and a hint naming blind-cut-through vs through-stops-short
- [ ] 3.2 Add `tests/test_quality_gate.py` cases: matching count passes, a blind hole built through fails with the right numbers, a plan without `through_count` emits nothing

## 4. Prompt and docs

- [ ] 4.1 Add the through/blind drawing rule and the `through_count` instruction (closed openings only, edge notch is 0, vent grid is N) to `prompts/planning.md` next to the `interfaces[]` rule (3b)
- [ ] 4.2 Document `through_hole_count_mismatch` in the `quality_gate.py` entry of `reference/scripts.md`
- [ ] 4.3 Run `uv run pytest tests/test_plan.py tests/test_mesh_io.py tests/test_quality_gate.py` and `ruff check`/`ruff format` on changed files
