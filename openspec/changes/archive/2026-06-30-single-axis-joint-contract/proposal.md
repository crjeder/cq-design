## Why

`plan_validate._check_kinematics` only checks that a joint's `unit` matches the block's `dof.unit`;
it never checks that the joint `type` or axis or range actually match. A `revolute` wish declared
against a `ball_socket` block, or a hinge swept about the wrong axis, passes validation today. The
gate is the safety net, but it lets a physically meaningless joint through to the (expensive)
geometric sweep. This closes that hole with a real satisfaction check: a joint is valid when the
block's degree of freedom (reality) covers what the plan asks for (wish) in **type, axis, and range**.

This is the first, shippable slice of the parked `joint-contract` exploration (see
`openspec/changes/joint-contract/`). It depends on no other in-flight work: the multi-union
machinery it eventually composes with already shipped (`multi-union-parts`). The Topology-1 block
rewrite and spherical (ball) contract are explicitly out of scope here.

## What Changes

- **Reshape `dof` to a vector model in block coordinates.** A `dof` carries `direction` (the slide
  direction for `prismatic`, the rotation axis for `revolute`) and, for `revolute` only, `origin`
  (a point on the axis -- the pivot). **BREAKING**: `dof.axis` (the `X`/`Y`/`Z` string) and
  `dof.unit` are removed; `unit` is derived from `type` (`deg` for `revolute`, `mm` for `prismatic`).
  `type` and `mechanical_limit` are kept as-is (the existing range semantics -- a nominal full range
  the authored-pose-relative `required_range` must fall within -- are unchanged). No angular
  reference vector is stored -- sign comes from the axis direction (right-hand rule) and the zero
  comes from the block's authored pose (already mandated by `printable-unit-model`).
- **Add the satisfaction check** to `plan_validate._check_kinematics`, replacing the `unit==`-only
  check. For each `revolute`/`prismatic` joint: (1) **type** must match the block's `dof.type`;
  (2) **axis** must match after pushing the block's `dof` vectors through the moving union's
  `placement` -- `revolute` requires coaxial (same line: origin + direction), `prismatic` requires
  parallel (direction only). Each failure is a structured `joint_contract` error. The **range** arm
  of the contract (required range within the block's `mechanical_limit`) already exists as the
  numeric range check and is unchanged; type + axis are the new arms.
- **Drop the now-redundant plan `unit` field** from each `kinematics` entry. **BREAKING**: the
  kinematics entry no longer carries `unit` (derived from `type`).
- **Spherical joints are not contract-checked (parked).** Ball joints keep their existing `dof`;
  the satisfaction check applies only to `revolute` and `prismatic` and skips `spherical` with no
  error, pending the parked spherical model.
- **No block geometry changes.** The joint blocks keep their current one-body-per-block topology;
  only the `dof` descriptor's shape changes. Merging the half-blocks into joint-owning multi-union
  blocks is a separate, later slice.

## Capabilities

### New Capabilities
- `joint-contract`: a declared joint is satisfied only when the referenced block's degree of freedom
  covers the plan's wish in type and axis (placement-transformed; revolute coaxial, prismatic
  parallel); together with the existing range check this forms the joint contract. Failures are
  structured `joint_contract` errors. Applies to revolute and prismatic; spherical is skipped.

### Modified Capabilities
- `kinematic-range-validation`: the `dof` descriptor is reshaped to the block-coordinate vector model
  (`direction`, revolute `origin`; `unit` derived; `axis` string and `unit` removed; `type` and
  `mechanical_limit` kept), and the plan `kinematics` entry drops `unit`. The existing range check
  and sweep requirements are unchanged.

## Impact

- Validation: `src/plan_validate.py` (`_check_kinematics` -- the satisfaction algebra), reusing
  `src/placement.py` to transform the block-frame `dof` vectors into the assembled frame.
- Schema: `src/blocks/inventory_schema.json` (`dof` shape), `src/build_plan_schema.json` (drop
  `kinematics[].unit`).
- Inventory: `src/blocks/inventory.json` -- migrate `dof` on the revolute/prismatic joint blocks
  (`hinge_leaf`, `pin_hinge`, `dovetail_groove`, `dovetail_tongue`) to the vector model; `ball_stud`
  / `ball_socket` keep a (now unchecked) spherical `dof`.
- Kinematic sweep: `src/kinematic_check.py` keeps reading `dof["mechanical_limit"]` (unchanged) but
  reads `dof.get("unit")` today; migrate that one read to a unit derived from `dof.type` so dropping
  `dof.unit` does not break the sweep stage's numeric pre-check.
- Tests: `tests/test_plan_validate.py` (type/axis/range mismatch -> `joint_contract` error; valid
  joint passes), and any kinematic-check fixtures that hand-write the old `dof`/`unit` shape.
- Out of scope: Topology-1 block merge (multi-union joint blocks), spherical/ball contract,
  derived kinematics (dropping the plan's redundant assembled-axis fields).
