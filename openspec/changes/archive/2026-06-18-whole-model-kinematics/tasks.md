## 1. Schema: unions, plates, placement

- [x] 1.1 Add a per-part (union) `plate` tag and an optional `placement`
      (`translate_mm` + ordered `rotate` list of `{axis, angle_deg}`) to
      `src/build_plan_schema.json`; default one union per plate, absent placement =
      identity
- [x] 1.2 Change the `kinematics` entry schema: replace `moving_part`/`fixed_part`
      with `moving_union`; drop the enumerated fixed part (fixed set derived); make
      `required_range` relative to the authored pose, allow negative/straddling
      values, add per-bound inclusivity (`lo_inclusive`/`hi_inclusive`, default
      closed/closed)
- [x] 1.3 Extend `src/plan_validate.py`: every part resolves a `plate`;
      `placement` axes are valid; `kinematics.moving_union` references an existing
      part; keep the block `dof`/`unit` cross-checks

## 2. Placement helper

- [x] 2.1 Add a shared placement utility (`src/placement.py`): `to_matrix` (4x4 for
      trimesh) and `apply_cq` (CadQuery) from a `placement` dict (rotations in order
      about X/Y/Z through origin, then translate)

## 3. Model-level export (`src/model_export.py`)

- [x] 3.1 Load each union's `result`, apply its placement, emit one 3MF with each
      union as a separately named object carrying its `plate` metadata (assembled
      pose baked into geometry); no boolean fusion of distinct unions
- [x] 3.2 Co-plated unions identifiable as a group via shared `plate` metadata
- [x] 3.3 Emit one assembled-pose STL per union (checker input) and one fused STL
      per plate that holds more than one union
- [x] 3.4 Direct multi-object 3MF writer in `src/exporters/threemf_multi.py`
      (CadQuery's built-in writer drops per-union names/metadata)

## 4. Kinematics: moving union vs rest of model

- [x] 4.1 In `src/kinematic_check.py`, the fixed set is every other union loaded
      from its assembled STL, each added as a separate named collision object;
      `motion_collision` carries a `colliding_union` field
- [x] 4.2 Respect bound inclusivity: include closed bounds, exclude open bounds; a
      collision at an excluded endpoint is not reported; range is relative to the
      authored pose (zero), may be negative/straddle zero
- [x] 4.3 Remove the print-in-place deferral: a single-plate multi-union joint is
      swept via its per-union meshes like any other (no special case remains)
- [x] 4.4 Keep the numeric `range_exceeds_limit` check and the structured issue
      contract; degrade gracefully when fcl is missing

## 5. Inventory / blocks

- [x] 5.1 Drop the `pin_hinge` kinematic special case (no code special case remains
      after the whole-model sweep); inventory `use` now documents it as two
      leaf-unions on a shared plate, kinematically identical to a pinned hinge

## 6. Planning prompt

- [x] 6.1 Update `prompts/planning.md`: emit unions with `plate` and (when needed)
      `placement`, treat the whole model as one assembly, and use `moving_union` in
      kinematics

## 7. Tests

- [x] 7.1 Placement helper: 4x4 matches expected rotate-then-translate
- [x] 7.2 Whole-model sweep: a blocked moving union mid-range -> `motion_collision`
      naming the colliding union
- [x] 7.3 Print-in-place two-union one-plate joint -> swept, not skipped
- [x] 7.4 Fixed set is all-other-unions (a third union in the path triggers a bind)
- [x] 7.5 Bound inclusivity: a collision exactly at an open bound is not reported
- [x] 7.6 Model export: named 3MF objects with placement + plate; per-union STL;
      fused-per-plate STL for a co-plated plate
- [x] 7.7 `plan_validate.py` rejects a `moving_union` referencing an unknown part
      and an invalid `placement` axis

## 8. Documentation

- [x] 8.1 `SKILL.md`: union/plate/placement planning, model-level export,
      whole-model sweep
- [x] 8.2 `CLAUDE.md`: add `model_export.py`/`placement.py`/`threemf_multi.py`
      rows; update kinematic-check notes and file layout
