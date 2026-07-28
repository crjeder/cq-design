# kinematic-range-validation Specification

## Purpose

Validate that movable joints in a generated assembly can achieve the range of
motion the design depends on, without binding against fixed parts. The stage
combines a mesh-free numeric check (required range vs. the joint block's
mechanical limit) with a collision sweep of the moving part against the fixed
part across the required range, emitting structured quality-gate findings.

## Requirements

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

---

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

---

### Requirement: The moving union is swept through the required range against the rest of the model

For each `kinematics` entry whose numeric check passes, the stage SHALL determine
the entry's swept subtree by recursively descending into `children`: the entry's
`moving_union` plus every union that is the `moving_union` of an entry nested
anywhere under this entry's `children`. The stage SHALL load the assembled mesh of
every union in the swept subtree and the assembled meshes of every union NOT in the
subtree, then step through `required_range` in increments of `step` (relative to
the authored-pose zero, including each closed bound and excluding each open bound).
At each step, the SAME per-step transform SHALL be applied identically to every
mesh in the swept subtree (rigid carry-along: a descendant joint's own required
range is not independently composed into the sweep -- it stays at its authored zero
relative to its mount), and collision SHALL be tested between each transformed
subtree mesh and the fixed set. The fixed set SHALL be added as **separate named
collision objects** (one per non-subtree union), not a single merged mesh, so the
binding union can be identified. Collision SHALL be tested with an in-process
trimesh collision manager backed by fcl. For a `revolute` joint the per-step
transform SHALL be a rotation by the step value about the line through
`axis_origin_mm` in direction `axis_dir`; for a `prismatic` joint it SHALL be a
translation along `axis_dir`. The sweep SHALL run in assembled (use) coordinates,
SHALL be bounded to `required_range`, and SHALL NOT sweep the full
`mechanical_limit`. A print-in-place joint whose unions share one plate SHALL be
validated the same way, using its per-union meshes; it SHALL NOT be deferred or
skipped for being a single print. A `motion_collision` issue SHALL name the
colliding union so the design loop can act on it.

#### Scenario: In-context binding is caught
- **WHEN** a hinge block could open 270 degrees in isolation but the box-body union
  blocks the lid union at 180 degrees within the assembled model
- **THEN** the sweep reports a `motion_collision` at the binding value naming the
  box-body union as the collider, even though the block's `mechanical_limit` is larger

#### Scenario: Range relative to authored pose may straddle zero
- **WHEN** an arm's `required_range` is `]-30, 90]` relative to its authored pose
- **THEN** the sweep covers from just inside -30 up to and including +90 (zero is the
  authored pose), excludes the open -30 bound, and a collision exactly at -30 is not
  reported

#### Scenario: Collision-free range passes
- **WHEN** every union in the swept subtree clears every non-subtree union at every
  swept step across the full required range
- **THEN** the stage reports the joint as passing and emits no collision issue

#### Scenario: Print-in-place joint is checked, not deferred
- **WHEN** both leaves of a print-in-place hinge are two unions sharing one plate
- **THEN** the stage sweeps the moving leaf union against the fixed leaf union (and
  any other unions) and reports binding or pass, rather than skipping the joint

#### Scenario: Only the required range is swept
- **WHEN** `required_range` is `[0, 90]` and `mechanical_limit` is `[0, 180]`
- **THEN** the sweep tests steps only across `0..90` and does not evaluate any
  position beyond 90

#### Scenario: A nested joint's union is carried along, not treated as fixed
- **WHEN** `shoulder`'s entry is swept and `shoulder`'s `children` array contains
  the `forearm` entry
- **THEN** at every step, `forearm`'s assembled mesh is transformed by the same
  rotation as `shoulder`'s mesh and is excluded from the fixed set, so `forearm`
  occupying `shoulder`'s rest-pose sweep path does not report a collision

#### Scenario: A sibling or unrelated union stays fixed during the sweep
- **WHEN** `shoulder`'s entry is swept and a `torso` union is not `shoulder`'s
  `moving_union`, and no entry nested under `shoulder`'s `children` has `torso` as
  its `moving_union`
- **THEN** `torso` remains in the fixed set and a collision between the swept
  subtree and `torso` is reported as `motion_collision`

---

### Requirement: Kinematics entries are validated at every nesting depth

`plan_validate.py` SHALL apply the existing per-entry checks (`moving_union`
resolves to a union id, `block` exists and carries a `dof`, and the joint-contract
type/axis arms) to every `kinematics` entry regardless of nesting depth, by
recursing into each entry's `children`. Because `children` nests entries directly
inside their mount point's JSON object, no entry can be its own ancestor, so no
separate cycle-detection pass is needed.

#### Scenario: A validation failure in a nested entry is still reported
- **WHEN** an entry nested three levels deep under `children` declares an unknown
  `block`
- **THEN** plan validation fails, reporting that entry's `joint_id` and the unknown
  block, the same as it would for a top-level entry

#### Scenario: A deeply nested valid chain passes
- **WHEN** a plan declares a `shoulder` -> `forearm` -> `hand` chain via nested
  `children`, each entry individually satisfying the joint contract
- **THEN** plan validation passes for all three entries

---

### Requirement: Findings use the existing structured issue contract

Every issue the stage emits SHALL use the same structure as other quality-gate
findings: `source`, `severity`, `type`, `message`, and `hint`, plus the
stage-specific fields named above (`required_range`, `mechanical_limit`, `unit`,
`binding_value`). The stage SHALL NOT introduce a parallel result format.

#### Scenario: Issue carries the standard fields
- **WHEN** the stage emits any finding
- **THEN** the finding includes `source`, `severity`, `type`, `message`, and
  `hint`

---

### Requirement: The stage degrades gracefully when fcl is unavailable

The stage SHALL degrade gracefully when the collision backend (`python-fcl` /
`fcl`) cannot be imported: it SHALL emit a single issue of type `check_skipped`
with `severity: "warning"` and SHALL NOT raise. The `range_exceeds_limit` check, which needs
no mesh or collision backend, SHALL still run.

#### Scenario: fcl missing skips the sweep but keeps the numeric check
- **WHEN** the collision backend cannot be imported
- **THEN** the stage emits one `check_skipped` warning, still performs the
  `required_range` within `mechanical_limit` check, and does not raise
