## 1. Plan schema + union resolution helper

- [x] 1.1 In `src/build_plan_schema.json`, add an optional `unions` array to a part item: each entry an object with required `id` (string) and optional `plate` (string). Document that absent `unions` means one union (id = part id), and that `placement` is part-level (applies to all the part's unions).
- [x] 1.2 Add a shared helper (e.g. `src/units.py` or in `placement.py`) `iter_unions(plan) -> list[(part, union_id, plate)]` that expands each part into its unions: declared `unions` (plate = `union.plate or part.plate or union_id`) or the single default `(part, part_id, part.plate or part_id)`. This is the one place the part->unions expansion lives.
- [x] 1.3 Add `resolve_unions(part, result) -> list[(union_id, Workplane)]`: a `dict` result -> `[(id, result[id]) for id in declared]` (validated keys); a plain `Workplane` -> `[(part_id, result)]`.

## 2. Result contract (loading, shim, preview)

- [x] 2.1 `src/exporters/__init__.py`: `_load_result` returns `Workplane | dict[str, Workplane]` (return `module.result` as-is; callers normalize via `resolve_unions`).
- [x] 2.2 `src/run_model_shim.py`: when `result` is a dict, auto-export one `<union_id>.stl` per key; a plain result keeps `<script>.stl` (today).
- [x] 2.3 `src/render_preview.py`: when `result` is a dict, render the union bodies together (combined preview) so the existing preview path still produces a PNG.

## 3. DFM wrapper validates each union

- [x] 3.1 `src/run_cadquery_model.py`: when the script `result` is a dict, validate each union body (watertight, thin-wall, overhang, manifold) and report per-union entries in the JSON `geometry`/`errors`; a single-`Workplane` result yields exactly today's single-body report (backward compatible).

## 4. Model export splits per union

- [x] 4.1 `src/model_export.py`: iterate via `resolve_unions(part, result)`; emit one named 3MF object + one `<union_id>.stl` per union (replace the per-part `makeCompound`); apply `part.placement` to each union; group plates per union via the `iter_unions` plate resolution.
- [x] 4.2 Cross-check: a `dict` result's keys equal the part's declared `unions`; mismatch -> a structured error (not a traceback).

## 5. Checks consume the full union set

- [x] 5.1 `src/kinematic_check.py`: build `all_union_ids` from `iter_unions(plan)` (every union across all parts), not `[part.id for part in parts]`; the per-union STL load and "fixed = every other union" are otherwise unchanged.
- [x] 5.2 `src/plate_clearance_check.py`: group co-plated unions via the `iter_unions` plate resolution (per union), replacing the part-level `_plate_of`.

## 6. Validation

- [x] 6.1 `src/plan_validate.py`: union-id uniqueness across the model (sub-union ids must not collide with each other or with part ids); `kinematics.moving_union` resolves to a union id in the expanded set; `unions[].plate` well-formed.

## 7. Tests

- [x] 7.1 A part declaring two unions with a `dict` result exports two named 3MF objects and two `<union_id>.stl` files; placing them on two plates yields two plate groups.
- [x] 7.2 Backward-compat: a single-`Workplane` part is byte-identical to today (one object, `<part_id>.stl`, plate = part.plate or part.id).
- [x] 7.3 `plan_validate` rejects duplicate union ids and a `moving_union` that names no union; `model_export` reports a structured error when result keys != declared unions.
- [x] 7.4 Kinematic + plate-clearance checks see a multi-union part's unions as distinct bodies (e.g. a print-in-place hinge authored as one part with two unions sweeps and clearance-checks like two parts do today).

## 8. Verification

- [x] 8.1 `uv run pytest tests/test_model_export.py tests/test_run_wrapper.py tests/test_plan_validate.py tests/test_kinematic_check.py tests/test_plate_clearance.py` pass (new + unchanged).
- [x] 8.2 `ruff check` / `ruff format` clean on changed files; mypy and basedpyright clean on changed `src/` modules.
- [x] 8.3 Update `CLAUDE.md` (model_export / the union-vs-part note) and `SKILL.md` (part loop: a part may emit a `dict` of unions); the planning prompt's "each part is a union" rule (`prompts/planning.md`) gains the multi-union option.
