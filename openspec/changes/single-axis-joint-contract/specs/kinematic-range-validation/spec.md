## MODIFIED Requirements

### Requirement: Joint blocks declare a degree-of-freedom descriptor in the inventory

A joint entry in `blocks/inventory.json` SHALL carry a `dof` object describing its
intrinsic degree of freedom when it participates in motion validation. The `dof`
object SHALL have `type` (one of `revolute`, `prismatic`, `spherical`, `fixed`),
`direction` (a three-element `[x, y, z]` vector, in block coordinates, giving the
block's local motion axis: the rotation axis for `revolute`, the slide direction for
`prismatic`), and `mechanical_limit` (a two-element `[lo, hi]` array giving the
block's nominal full range). A `revolute` `dof` SHALL also carry `origin` (a
three-element `[x, y, z]` point, in block coordinates, lying on the rotation axis --
the pivot); `prismatic` does not require `origin`, because translation is
position-independent. The `unit` SHALL be derived from `type` (`deg` for
`revolute`/`spherical`, `mm` for `prismatic`) and SHALL NOT be stored on the `dof`;
the legacy `axis` (an `X`/`Y`/`Z` string) and `unit` fields SHALL NOT be present. The
direction vector's sign fixes the positive sense of motion by the right-hand rule;
the zero of the range is the block's authored use pose (see `printable-unit-model`).
The `mechanical_limit` is a nominal sanity bound and SHALL NOT be treated as the
authoritative achievable range for a specific instance.

#### Scenario: Revolute joint declares an axis vector, pivot, and degree range
- **WHEN** a hinge block declares `dof`
- **THEN** its `type` is `revolute`, it carries a `direction` vector and an `origin`
  point in block coordinates, its derived unit is `deg`, and its `mechanical_limit`
  is a two-element array such as `[0, 180]`

#### Scenario: Prismatic joint declares a direction vector and millimetre range
- **WHEN** a sliding (dovetail) block declares `dof`
- **THEN** its `type` is `prismatic`, it carries a `direction` vector in block
  coordinates with no required `origin`, its derived unit is `mm`, and its
  `mechanical_limit` expresses travel in millimetres

#### Scenario: Legacy axis and unit fields are absent
- **WHEN** any joint block's `dof` is read
- **THEN** it carries no `axis` string and no `unit` field; the unit is derived from
  `type`

#### Scenario: Non-joint and flexure blocks omit dof
- **WHEN** a block has no rigid degree of freedom (a non-joint primitive, or a
  `living_hinge` flexure)
- **THEN** the block omits the `dof` descriptor and is not subject to kinematic
  validation

### Requirement: The build plan declares required range of motion per joint

`BUILD_PLAN.json` SHALL support an optional top-level `kinematics` array. Each
entry SHALL declare `joint_id`, `moving_union` (the id of the union that moves),
`block` (the joint block name), `axis_origin_mm` (a three-element world-space point
`[x, y, z]` in assembled coordinates), `axis_dir` (one of `X`, `Y`, `Z`), `type`
(the joint type), `required_range` (a `[lo, hi]` range the design depends on,
**relative to the block's authored pose**, which is the zero point), and `step` (the
sweep increment). The entry SHALL NOT carry a `unit` field: the unit is derived from
`type` (`deg` for `revolute`/`spherical`, `mm` for `prismatic`), matching the
block's derived `dof` unit. `required_range` MAY be negative and MAY straddle zero
(e.g. `]-30, 90]`), and SHALL carry per-bound inclusivity following mathematical
interval notation (an open bound need not be reached; a closed bound must be cleared;
default closed/closed). The fixed set SHALL be derived as every other union in the
model and SHALL NOT be enumerated in the entry.

#### Scenario: Plan declares a moving union and a partial required range
- **WHEN** a phone-holder arm union must fold from upright to flat
- **THEN** its `kinematics` entry declares `moving_union`, `type: "revolute"`, and
  `required_range: [0, 90]` with no `unit` field, and the fixed set is every other
  union in the model

#### Scenario: A kinematics entry carrying a unit field is rejected
- **WHEN** a `kinematics` entry includes a `unit` property
- **THEN** schema validation fails, because `unit` is derived from `type` and is not
  a plan field

#### Scenario: Plan without kinematics skips the stage
- **WHEN** a plan has no `kinematics` array or an empty one
- **THEN** the kinematic validation stage does not run and emits no findings
