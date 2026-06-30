## 1. dof vector model (schema + inventory)

- [x] 1.1 In `src/blocks/inventory_schema.json`, reshape the `dof` definition: remove `axis` (the
      `X`/`Y`/`Z` string) and `unit`; add `direction` (3-element number array, required) and `origin`
      (3-element number array); keep `type` and `mechanical_limit`. Require `origin` when `type` is
      `revolute` (and not for `prismatic`).
- [x] 1.2 In `src/blocks/inventory.json`, migrate the revolute/prismatic joint blocks
      (`hinge_leaf`, `pin_hinge`, `dovetail_groove`, `dovetail_tongue`) to the vector model: replace
      `axis: "Y"` with a `direction` vector along the authored axis, add `origin` on the revolute
      blocks, drop `unit`, keep `mechanical_limit`.
- [x] 1.3 In `src/blocks/inventory.json`, migrate `ball_stud`/`ball_socket`: drop `axis`/`unit`, add a
      `direction` vector, keep `type: "spherical"` and `mechanical_limit` (it stays unchecked).
- [x] 1.4 Confirm the migrated `inventory.json` validates against the updated schema, and that no
      `dof.axis` or `dof.unit` token remains under `src/blocks/` (grep).

## 2. Migrate existing dof consumers

- [x] 2.1 In `src/kinematic_check.py`, replace the `dof.get("unit")` read with a unit derived from
      `dof.type` (`deg` for `revolute`/`spherical`, `mm` for `prismatic`); leave the
      `dof["mechanical_limit"]` read unchanged.
- [x] 2.2 In `src/build_plan_schema.json`, remove `unit` from the `kinematics` entry: drop it from the
      entry's `required` list and `properties`, leaving `joint_id`, `moving_union`, `block`,
      `axis_origin_mm`, `axis_dir`, `type`, `required_range`, `step`.

## 3. Satisfaction check

- [x] 3.1 Add a numpy-free transform helper (rotate a vector and a point through a `placement`'s
      ordered X/Y/Z `angle_deg` steps plus translation) usable from the CadQuery-free plan-validate
      path; do not import `trimesh`/`placement.to_matrix` into that path.
- [x] 3.2 In `src/plan_validate.py` `_check_kinematics`, replace the `unit==` check with the
      satisfaction check: for each `revolute`/`prismatic` entry, verify (a) `type` matches the block's
      `dof.type`, and (b) the axis matches after transforming the block `dof` vectors by the moving
      union's `placement` -- revolute coaxial (direction parallel within epsilon AND plan
      `axis_origin_mm` on the transformed axis line), prismatic parallel (direction only). Emit
      `joint_contract` errors with the conflicting values; skip `spherical` with no error.
- [x] 3.3 Define the parallelism and point-on-line epsilon as module constants.

## 4. Tests

- [x] 4.1 In `tests/test_plan_validate.py`, assert a `revolute` wish against a `spherical` block
      yields a `joint_contract` type error; a revolute axis parallel-but-off-line yields a coaxial
      error; a prismatic parallel-but-offset axis passes; a fully matching joint passes; a `spherical`
      joint emits no `joint_contract` issue.
- [x] 4.2 Add a test that the transform helper agrees with `placement.to_matrix` on a known axis
      through a non-trivial (multi-rotation + translation) placement (this test MAY import trimesh).
- [x] 4.3 Update any kinematic-check fixtures/tests that hand-write the old `dof` (`axis`/`unit`) or
      the old `kinematics` `unit` field to the new shapes.

## 5. Verification

- [x] 5.1 `uv run pytest tests/test_plan_validate.py tests/test_kinematic_check.py tests/test_blocks.py`
      pass.
- [x] 5.2 Confirm `tests/test_plan_validate.py` still runs with no CadQuery and no trimesh import in
      the production validate path (the helper is numpy/trimesh-free).
- [x] 5.3 `ruff check` / `ruff format` clean on changed files; mypy and basedpyright clean on
      `src/plan_validate.py`.
- [x] 5.4 Both JSON schema files are valid JSON.
