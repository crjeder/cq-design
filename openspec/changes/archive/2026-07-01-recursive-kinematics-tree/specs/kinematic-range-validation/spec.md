## MODIFIED Requirements

### Requirement: The build plan declares required range of motion per joint

`BUILD_PLAN.json` SHALL support an optional top-level `kinematics` array. Each
entry SHALL declare `joint_id`, `moving_union` (the id of the union that moves),
`block` (the joint block name), `axis_origin_mm` (a three-element world-space point
`[x, y, z]` in assembled coordinates), `axis_dir` (one of `X`, `Y`, `Z`), `type`
(the joint type), `required_range` (a `[lo, hi]` range the design depends on,
**relative to the block's authored pose**, which is the zero point), and `step` (the
sweep increment). The entry MAY also declare `children`: an array of nested
`kinematics` entries (the same shape, recursively) that are mounted on this entry's
`moving_union`, establishing that each child's swept subtree (see the sweep
requirement below) is nested under this entry. A top-level entry -- one not listed
in any other entry's `children` -- is mounted on the static frame, the same
fixed-set derivation as before this field existed. Because a child is nested
directly inside its parent's JSON object, the `kinematics` array is a forest by
construction: a joint cannot reference itself or an ancestor as its own child. The
entry SHALL NOT carry a `unit` field: the unit is derived from `type` (`deg` for
`revolute`/`spherical`, `mm` for `prismatic`), matching the block's derived `dof`
unit. `required_range` MAY be negative and MAY straddle zero (e.g. `]-30, 90]`),
and SHALL carry per-bound inclusivity following mathematical interval notation (an
open bound need not be reached; a closed bound must be cleared; default
closed/closed).

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

## ADDED Requirements

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
