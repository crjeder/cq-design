## 1. Geometry-level thickness field

- [x] 1.1 Add a `thickness` module/function in `src/measure_stl.py` that samples surface points (capped count) and ray-casts inward along the inverse normal to measure local thickness. (Implemented with a vectorized Moeller-Trumbore ray cast in numpy via `_ray_thickness`, not `mesh.ray.intersects_location`: trimesh's ray engine requires `rtree`, a new dependency the design excludes.)
- [x] 1.2 Group sampled hits into thin regions (by face adjacency) and compute per-region `thickness_mm`, representative `xyz`, thin direction (dominant normal axis via eigen-decomposition), the XY-vs-Z classification via `|n . z_hat|`, and `thickness_mean_mm` (shoulder proxy for remedy typing).
- [x] 1.3 Snap each thin region to the nearest `flat_face`/`cylinder` within a radius; emit the feature label and distance, null beyond the radius. (Added `center_xy_mm` to `flat_faces` output so snapping is uniform 3D.)
- [x] 1.4 Add thin-region results to the `measure()` return dict without renaming existing keys.

## 2. Script/plan-level extent check

> Resolved via schema extension (design Open Question #2): `blocks_needed` items
> may now be objects `{name, extents_mm:[x,y,z]}`. The check runs in
> `plan_validate.py` (before any code/mesh) as a non-failing advisory finding,
> consistent with the geometry-level `thin_interface` being a warning.

- [x] 2.1 `check_block_thinness` in `plan_validate.py` flags `min(extents_mm) < wall_min_mm` per block, naming the part id, block name, and axis. Reported as a finding in `main()` (does not fail validation).
- [x] 2.2 Per-block extents are sourced from the new object form of `blocks_needed` in `BUILD_PLAN.json`; the schema accepts string or object, `planning.md` instructs the planner to use the object form when the instance size is known.

## 3. Wrapper integration (run_cadquery_model.py)

- [x] 3.1 Replace/augment `_check_thin_walls` to consume the thickness field, skip regions classified thin-in-Z (benign flat slabs), and emit a typed `thin_interface` error for XY-thin regions with location, `thickness_mm`, `equiv_diameter_mm`, threshold crossed, and thin direction. (Replaced by `_check_thin_interfaces`.)
- [x] 3.2 Compute the remedy `hint` keyed to which threshold was crossed (thicken / reorient-with-overhang-tradeoff / brittle-all-perimeter / fillet on sharp taper); for reorient, report the rotation axis that brings the thin direction parallel to Z. (`_thin_interface_hint`.)
- [x] 3.3 Ground thresholds in FDM reality: derive the brittle threshold from extrusion line width (~4x); surface `--wall-min` / `--line-width` as wrapper args.
- [x] 3.4 Add thin-region findings to the `geometry` block of the wrapper JSON.

## 4. Quality gate aggregation

- [x] 4.1 Include thin-interface findings in `quality_gate.py` aggregated DFM report alongside overhang and orca-check results. (Flow through the existing `errors[]` pass-through as warnings; quality_gate now passes a nozzle-derived `--line-width`.)

## 5. Tests

- [x] 5.1 Add fixtures (in `tests/test_thin_interfaces.py`): thin vertical fin beside thick mass, flat slab thin only in Z, fin-on-plate, and a CadQuery union-fin model for the wrapper. (Neck and emergent-sliver are the same XY-thin detection path as the fin, so not separately fixtured.)
- [x] 5.2 Assert thin vertical fin is detected at ~2 mm and classified thin-in-XY despite dominant adjacent mass; assert the flat 1 mm slab is classified thin-in-Z and NOT flagged.
- [x] 5.3 Assert script-level extent check flags an intentionally thin block with correct attribution before meshing (`test_thin_block_flagged_with_attribution`, `test_thick_blocks_no_findings`, `test_block_object_form_validates` in `tests/test_plan_validate.py`).
- [x] 5.4 Assert `thin_interface` error shape (location, thickness, equiv diameter, threshold, thin direction, nearest feature, hint) and `geometry`-block presence.
- [x] 5.5 Assert nearest-feature snap returns a feature when near and null when beyond the radius (unit tests of `_nearest_feature`).
- [x] 5.6 Remove/replace the superseded fill-ratio test. (No dedicated fill-ratio test existed; the `_check_thin_walls` function it covered was replaced by `_check_thin_interfaces`.)

## 6. Orientation priority policy (reference content)

- [x] 6.1 Rewrite `reference/FDM 3D Print Design Guidelines.md` `Print Orientation > General Orientation Rules` to state the priority order (1: stability / largest flat face on bed; 2: minimize overhangs/support given that footprint) and the fallback (if no orientation satisfies both, split the part and escalate to the planning phase). Keep it part-agnostic; it is injected into both prompts via `{{FDM_GUIDELINES}}`.
- [x] 6.2 Verify the rewritten section renders correctly in `planning.md` and `part.md` after `{{FDM_GUIDELINES}}` substitution. (Section sits under `## Print Orientation`, tagged `applies_to: always`, so it is always injected into both prompts; injection is performed by the skill, no renderer script to run.)

## 7. Docs & checks

- [x] 7.1 Update `CLAUDE.md` core-scripts table and JSON-contract notes to mention thin-interface fields.
- [x] 7.2 Run `ruff check --fix` and `ruff format` on changed Python files; run `uv run pytest tests/`. (88 passed.)
