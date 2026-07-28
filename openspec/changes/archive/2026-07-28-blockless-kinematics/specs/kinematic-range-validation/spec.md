## MODIFIED Requirements

### Requirement: The build plan declares required range of motion per joint

`BUILD_PLAN.json` SHALL support an optional top-level `kinematics` array. Each
entry SHALL declare `joint_id`, `moving_union` (the id of the union that moves),
`axis_origin_mm` (a three-element world-space point `[x, y, z]` in assembled
coordinates), `axis_dir` (one of `X`, `Y`, `Z`), `type` (the joint type),
`required_range` (a `[lo, hi]` range the design depends on, **relative to the
union's authored pose**, which is the zero point), and `step` (the sweep
increment). `block` (the joint block name) SHALL be optional: an entry that omits
it is a **block-less** (directly-declared) joint -- built from raw primitives with
no inventory backing -- and `axis_origin_mm`/`axis_dir`/`type`/`required_range`/
`step` fully specify its motion on their own. An entry that omits `block` MAY
declare `mechanical_limit` (a `[lo, hi]` array in the same shape and unit as a
block's `dof.mechanical_limit`) as its own nominal sanity bound; `mechanical_limit`
is ignored when `block` is present, since the block's `dof` remains authoritative.
The entry MAY also declare `children`: an array of nested `kinematics` entries (the
same shape, recursively) that are mounted on this entry's `moving_union`,
establishing that each child's swept subtree (see the sweep requirement below) is
nested under this entry. A top-level entry -- one not listed in any other entry's
`children` -- is mounted on the static frame, the same fixed-set derivation as
before this field existed. Because a child is nested directly inside its parent's
JSON object, the `kinematics` array is a forest by construction: a joint cannot
reference itself or an ancestor as its own child. The entry SHALL NOT carry a
`unit` field: the unit is derived from `type` (`deg` for `revolute`/`spherical`,
`mm` for `prismatic`), matching the block's derived `dof` unit when a block is
present. `required_range` MAY be negative and MAY straddle zero (e.g.
`]-30, 90]`), and SHALL carry per-bound inclusivity following mathematical
interval notation (an open bound need not be reached; a closed bound must be
cleared; default closed/closed).

#### Scenario: Plan declares a moving union and a partial required range
- **WHEN** a phone-holder arm union must fold from upright to flat
- **THEN** its `kinematics` entry declares `moving_union`, `type: "revolute"`, and
  `required_range: [0, 90]` with no `unit` field

#### Scenario: A kinematics entry carrying a unit field is rejected
- **WHEN** a `kinematics` entry includes a `unit` property
- **THEN** schema validation fails, because `unit` is derived from `type` and is not
  a plan field

#### Scenario: Plan without kinematics skips the stage
- **WHEN** a plan has no `kinematics` array or an empty one
- **THEN** the kinematic validation stage does not run and emits no findings

#### Scenario: A joint declares the joints mounted on it
- **WHEN** a `shoulder` entry's `children` array contains a `forearm` entry
- **THEN** the plan validates, and the sweep requirement below carries `forearm`
  along whenever `shoulder`'s entry is swept

#### Scenario: A joint not nested under any children is mounted on the static frame
- **WHEN** a `kinematics` entry is a top-level array element, not listed in any
  other entry's `children`
- **THEN** it behaves exactly as it did before this field existed: no other joint's
  sweep carries it along

#### Scenario: A joint built from raw primitives omits block and declares its axis directly
- **WHEN** a custom clevis/tongue hinge has no matching inventory block
- **THEN** its `kinematics` entry omits `block` and still declares `moving_union`,
  `axis_origin_mm`, `axis_dir`, `type`, `required_range`, and `step`, and the plan
  validates

#### Scenario: A block-less entry declares its own mechanical_limit
- **WHEN** a block-less entry wants a numeric sanity bound
- **THEN** it declares `mechanical_limit: [lo, hi]` directly on the entry, in the
  same shape as a block's `dof.mechanical_limit`

#### Scenario: mechanical_limit on a block-backed entry is ignored
- **WHEN** an entry names a `block` and also declares `mechanical_limit`
- **THEN** the block's `dof.mechanical_limit` is used for the numeric check, not
  the entry's `mechanical_limit`

---

### Requirement: Required range is checked against the block mechanical limit

For each `kinematics` entry, the stage SHALL determine a mechanical-limit source:
the referenced block's `dof.mechanical_limit` when `block` is present, otherwise
the entry's own `mechanical_limit` when declared. When a source is available, the
stage SHALL verify the declared `required_range` lies within it; when the required
range falls outside, the stage SHALL emit an issue of type `range_exceeds_limit`
carrying the requested range, the limit, and the unit. When neither a block nor an
entry `mechanical_limit` is available (a block-less entry with none declared), the
stage SHALL NOT silently skip the check: it SHALL emit an issue of type
`range_check_not_applicable` (severity `warning`) recording that the numeric arm
did not apply for that joint, and SHALL still proceed to the collision sweep for
that entry. This check SHALL run without loading any mesh.

#### Scenario: Required range within limit passes the numeric check
- **WHEN** `required_range` is `[0, 90]` and `mechanical_limit` is `[0, 180]`
- **THEN** no `range_exceeds_limit` issue is emitted

#### Scenario: Required range exceeds limit is flagged
- **WHEN** `required_range` is `[0, 270]` and `mechanical_limit` is `[0, 180]`
- **THEN** the stage emits a `range_exceeds_limit` issue reporting both ranges and
  does not need to load any STL to do so

#### Scenario: Block-less entry with its own mechanical_limit is checked the same way
- **WHEN** a block-less entry declares `mechanical_limit: [0, 180]` and
  `required_range: [0, 270]`
- **THEN** the stage emits a `range_exceeds_limit` issue exactly as it would for a
  block-backed entry with the same limit

#### Scenario: Block-less entry with no mechanical_limit reports the numeric arm as not applicable
- **WHEN** a block-less entry declares no `mechanical_limit`
- **THEN** the stage emits a `range_check_not_applicable` warning naming the joint,
  does not emit a `range_exceeds_limit` issue, and still runs the collision sweep
  for that entry
