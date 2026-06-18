## 1. Shared profile helper

- [x] 1.1 Add `_drop_profile(r, angle, apex, flat=0.0)` to `blocks/connectors.py`: builds the X-Z profile (upper or lower arc per `apex`, two 45-degree faces from the equator points, optional flat truncation when `flat > 0`).
- [x] 1.2 Refactor `teardrop_bore` to call `_drop_profile(r, angle, apex="up")` and confirm the closing path is unchanged (pointed peak, `flat=0`).

## 2. teardrop_post block

- [x] 2.1 Implement `teardrop_post(d, length, angle=45, flat=1.2)` using `_drop_profile(r, angle, apex="down", flat=...)`, extruded `length` along the axis, additive orientation (flat bottom at min Z, axis +Y).
- [x] 2.2 Add a module-level useful-diameter threshold constant (default 3.0 mm).
- [x] 2.3 Clamp the effective flat (to `d/2`) when `flat >= d` so inclined faces always exist; `warnings.warn` when `d` is below the threshold; never raise.

## 3. Registration and export

- [x] 3.1 Add the `teardrop_post` descriptor to `blocks/inventory.json` (module `blocks.connectors`, params, `axis` interface, `use` string with min-diameter guidance and the 45-degree-rotated-cube redirect for functional pairs).
- [x] 3.2 Re-export `teardrop_post` from `blocks/__init__.py`.

## 4. Documentation

- [x] 4.1 Add a "Protrusions & Pegs" note to `reference/FDM 3D Print Design Guidelines.md` covering the three-way choice: `teardrop_bore` (hole roof), `teardrop_post` (free peg underside), rotated cube (functional pair). Planner guidance is carried by the inventory `use` string, so `prompts/planning.md` needs no edit.

## 5. Tests

- [x] 5.1 Add `teardrop_post` tests in `tests/test_blocks.py`: returns a watertight solid; unions onto a box watertight; underside faces <= 45 degrees; flat bottom at min Z.
- [x] 5.2 Add small-feature tests: tiny `d` builds and warns; oversized `flat` is clamped and still builds; neither raises.
- [x] 5.3 `teardrop_bore` regression locked by existing `test_teardrop_bore_dimensions_and_epsilon` (diameter, `depth + _EPS`) and `test_teardrop_bore_upper_profile_is_a_peak` (peak not arc), now run against the refactored code.
- [x] 5.4 Ran `pytest tests/test_blocks.py` (59 passed) and `tests/test_plan_validate.py` (12 passed); inventory validates (30 blocks).
