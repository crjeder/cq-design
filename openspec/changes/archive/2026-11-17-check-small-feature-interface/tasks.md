## 1. Spike and interface function

- [x] 1.1 Spike in CadQuery: confirm `intersect` behaviour for solid/solid overlap and for coplanar face/face contact on these fixtures: cone on a cube face, cone sunk 0.1 mm, cone on a cube edge, post on three 0.2 x 1 mm patches, post on a 3 mm column. Record what each returns (empty, degenerate, faces) and settle the fallback in design.md if needed
- [x] 1.2 Create `src/interface_area.py` with `interface_area(before, tool) -> (area_mm2, centroid)`: `min(S_b_in, S_t_in)` where each is the summed area of one shape's faces intersected with the other solid (bbox-prefiltered); edge or point contact returns 0
- [x] 1.3 Create `tests/test_interface_area.py` with the five fixtures above plus a through-pin, asserting the areas in the spec scenarios (cone base area, cone cross-section when sunk, half base on an edge, 0 beyond the edge, about 0.6, about 7)

## 2. Profile constraint

- [x] 2.1 Add optional `interface_min_area_mm2` (number, exclusiveMinimum 0) to `constraints` in `src/printer_profile_schema.json` and the matching block in `src/build_plan_schema.json`
- [x] 2.2 Set `interface_min_area_mm2: 4.0` in `src/profile.default.json`
- [x] 2.3 Add tests to `tests/test_printer_profile_validate.py`: default validates, older profile without the field validates, 0 and negative fail

## 3. Wire into Part.place

- [x] 3.1 In `Part.place` (`src/blocks/part.py`), for `op == "union"` measure each tool in `tools` against `before` with `interface_area`; set `step["interface"] = {area_mm2, location_xyz_mm}`; add the threshold to the `place` key chain so cached steps stay valid
- [x] 3.2 Raise `self._error(step, "small_interface", ...)` when the area is below the constraint (default 4.0), with `area_mm2`, `equiv_diameter_mm`, threshold, instance id, `location_xyz_mm`, and a hint offering a footprint at or above the threshold such as a column to the build plate
- [x] 3.3 Add `Part` tests: failing step on a post placed on slivers, passing step on a column, multi-point `at` with one bad copy reported separately, `cut` and `base` steps unmeasured, a cached rerun returning the same `interface`
- [x] 3.4 Confirm `step_worker` passes the `small_interface` error through its report and the existing probe and step tests are unchanged

## 4. Prompts and docs

- [x] 4.1 Add a rule to `prompts/planning.md` and `skill/phase3_build.md`: a feature stacked on another body needs an interface of at least `interface_min_area_mm2`, for example a column to the build plate
- [x] 4.2 Document `small_interface`, the step `interface` entry, and the constraint in `reference/scripts.md`; add `src/interface_area.py` and its test to `FILES.md`
- [x] 4.3 Run `uv run pytest tests/test_interface_area.py tests/test_printer_profile_validate.py` plus the existing step and probe tests, and `ruff check` / `ruff format` on changed files
