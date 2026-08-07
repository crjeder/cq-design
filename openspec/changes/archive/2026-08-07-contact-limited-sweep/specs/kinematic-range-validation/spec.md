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

The entry MAY also declare `stop_on_contact` (a boolean, default `false`). When
`false`, the entry's required range is a hard requirement and interference anywhere
in it is an error, the behaviour that predates this field. When `true`, the entry
declares a **contact-limited** joint: one whose closed (or fully-travelled) position
is defined by resting against another body rather than by reaching a specific value.
For such a joint the sweep stops at first real interference and reports how far it
got, instead of failing (see the sweep requirement below).

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

#### Scenario: A folding leaf whose closed position is a contact stop declares stop_on_contact
- **WHEN** a cradle leaf folds up until it rests against a cover plate, with no
  specific closing angle required
- **THEN** its `kinematics` entry declares `stop_on_contact: true` alongside the
  nominal `required_range` it would ideally reach

#### Scenario: stop_on_contact defaults to false
- **WHEN** a `kinematics` entry omits `stop_on_contact`
- **THEN** the entry is treated as a hard-range joint, exactly as before this field
  existed

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
relative to its mount), and interference SHALL be tested between each transformed
subtree mesh and the fixed set. The fixed set SHALL be added as **separate named
collision objects** (one per non-subtree union), not a single merged mesh, so the
binding union can be identified. Interference SHALL be determined by the shared
interference primitive under volume semantics, so designed flush contact at a joint
does not count as binding. For a `revolute` joint the per-step transform SHALL be a
rotation by the step value about the line through `axis_origin_mm` in direction
`axis_dir`; for a `prismatic` joint it SHALL be a translation along `axis_dir`. The
sweep SHALL run in assembled (use) coordinates, SHALL be bounded to
`required_range`, and SHALL NOT sweep the full `mechanical_limit`. A print-in-place
joint whose unions share one plate SHALL be validated the same way, using its
per-union meshes; it SHALL NOT be deferred or skipped for being a single print. A
`motion_collision` issue SHALL name the colliding union so the design loop can act
on it, and SHALL carry the measured intersection volume at the binding pose.

**Travel order.** The sweep SHALL visit poses in the order the mechanism actually
moves through them: starting at the authored pose (zero) and travelling **outward**,
never starting at a far bound and travelling inward. `required_range` is declared
relative to the authored zero, so the bound nearest zero is where the motion begins.
Concretely: a wholly non-negative range is travelled from `lo` up to `hi`; a wholly
non-positive range (e.g. `[-90, 0]`) is travelled from `hi` down to `lo`; and a range
straddling zero is travelled as **two independent arms** from zero -- one to `hi`, one
to `lo` -- each arm evaluated separately so interference on one side does not prevent
the other side from being swept.

Travel order is what makes "first interference" mean the mechanism's stop rather than
an arbitrary sample. Without it, a fold declared `[-90, 0]` would be evaluated starting
at -90 -- the deepest interpenetration, a pose the mechanism reaches only by passing
through its own stop -- and the first sample would be reported as the stop.

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

#### Scenario: A negative range is travelled from zero downward
- **WHEN** a fold declares `required_range: [-90, 0]` and first interferes at -53.5
  degrees
- **THEN** the sweep starts at 0 and travels toward -90, reporting the stop at -53.5
  rather than at -90

#### Scenario: A straddling range sweeps each side independently from zero
- **WHEN** a joint declares `required_range: [-30, 90]` and interference occurs at +40
  degrees but the negative side is clear to -30
- **THEN** the positive arm stops at +40 and the negative arm still reaches -30, and
  the achieved range reflects both sides rather than the negative side being skipped

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

#### Scenario: Designed flush contact during the sweep does not bind
- **WHEN** a swept pose brings the moving subtree into face-to-face contact with a
  fixed union whose true intersection volume is within tolerance
- **THEN** the sweep continues past that pose and reports no `motion_collision` for it

---

### Requirement: The stage degrades gracefully when fcl is unavailable

The stage SHALL degrade gracefully when the geometry backend cannot be imported: it
SHALL emit a single issue of type `check_skipped` with `severity: "warning"` and SHALL
NOT raise. The `range_exceeds_limit` check, which needs no mesh or geometry backend,
SHALL still run.

The backend is the whole set the interference primitive requires -- trimesh, the
collision backend (`python-fcl` / `fcl`), and the boolean engine used to measure
overlap volume -- treated as one unit. Any one of them missing SHALL skip the sweep
rather than fall back to a weaker interference measure, matching the primitive's own
no-fallback rule.

#### Scenario: fcl missing skips the sweep but keeps the numeric check
- **WHEN** the collision backend cannot be imported
- **THEN** the stage emits one `check_skipped` warning, still performs the
  `required_range` within `mechanical_limit` check, and does not raise

#### Scenario: Boolean engine missing skips the sweep the same way
- **WHEN** trimesh and the collision backend import but the boolean engine does not
- **THEN** the stage emits one `check_skipped` warning and does not sweep, rather than
  measuring interference by any substitute means

---

## ADDED Requirements

### Requirement: A cut-short sweep reports the range the joint actually achieved

Whenever a sweep is cut short by interference, the finding it emits SHALL state the
range the joint achieved before stopping -- not only that it failed. The finding SHALL
carry the achieved range, the union the joint stopped against, and the measured
intersection volume at the stopping pose.

The achieved range SHALL be expressed as an interval `[achieved_lo, achieved_hi]`
around the authored zero, one bound per direction of travel. A side that swept clear
contributes its declared bound; a side cut short contributes its stopping value. For a
range straddling zero this means a stop on one side does not misreport the other side
as unreachable.

The stage SHALL refine each reported stopping value by bisecting between the last clear
swept value and the first binding swept value on that side, so the reported value does
not depend on the granularity of `step`.

A sweep that completes its full required range SHALL continue to emit no finding: the
achieved range equals the required range by definition, so a separate report would add
noise without information. The stage SHALL NOT introduce a new severity tier for such
a report, because the quality gate partitions findings into `error` and `warning` only
and a third tier would be silently discarded.

#### Scenario: A binding joint reports how far it travelled
- **WHEN** a joint with `required_range: [0, 90]` first interferes near 54 degrees
- **THEN** the finding reports the achieved range as approximately `[0, 54]`, names
  the union it stopped against, and reports the intersection volume at that pose

#### Scenario: A negative-range fold reports the near-zero stop
- **WHEN** a joint with `required_range: [-90, 0]` first interferes at -53.5 degrees
  travelling from zero
- **THEN** the finding reports the achieved range as approximately `[-53.5, 0]`, not
  `[-90, -90]`

#### Scenario: Each side of a straddling range reports its own bound
- **WHEN** a joint with `required_range: [-30, 90]` stops at +40 on the positive side
  and sweeps the negative side clear
- **THEN** the achieved range is approximately `[-30, 40]`

#### Scenario: The reported stop value is refined below step granularity
- **WHEN** a sweep with `step: 5` finds the last clear pose at 50 degrees and the
  first binding pose at 55 degrees
- **THEN** the stage bisects between them and reports a stopping value between 50 and
  55 rather than reporting 55

#### Scenario: A clear sweep stays silent
- **WHEN** the swept subtree clears every fixed union across the whole required range
- **THEN** the stage emits no finding for that entry, as before this requirement
  existed

---

### Requirement: A contact-limited joint reports its stop instead of failing

For an entry declaring `stop_on_contact: true`, first real interference SHALL be
treated as the joint's **mechanical stop**, not as a defect. The stage SHALL stop the
sweep there and SHALL NOT emit a `motion_collision` error for that pose, because the
poses beyond the stop are ones the physical mechanism cannot reach and so cannot
collide in.

When a contact-limited joint stops short of its `required_range`, the stage SHALL
emit a finding of severity `warning` (not `error`) reporting the achieved range, the
union it stopped against, and the shortfall against the required range. Falling short
is information for the designer to accept or act on -- a folding leaf that rests
against its plate at 54 degrees instead of a nominal 90 may be exactly the intended
design -- so it SHALL NOT fail the gate on its own.

The minimum clearance observed across the travelled portion of the range SHALL be
reported alongside the stop, so a joint that merely grazes its whole travel is
distinguishable from one that swings freely until it lands on its stop.

#### Scenario: A contact-limited fold stops against its mating body
- **WHEN** a cradle leaf with `stop_on_contact: true` and `required_range: [-90, 0]`
  first contacts the plate at -53.5 degrees
- **THEN** the stage emits a `warning` reporting that the joint achieves -53.5 of the
  required -90 degrees, stopping against the plate union, and emits no
  `motion_collision` error

#### Scenario: A contact-limited joint reaching its full range is clean
- **WHEN** a `stop_on_contact` joint travels its entire required range without
  interference
- **THEN** the stage emits no warning about a shortfall and reports the full range as
  achieved

#### Scenario: A hard-range joint is unaffected
- **WHEN** an entry omits `stop_on_contact` (or sets it `false`) and interference
  occurs inside its required range
- **THEN** the stage emits a `motion_collision` error exactly as it did before this
  requirement existed

#### Scenario: A stale union suppresses the achieved-range report for that entry
- **WHEN** an entry's moving subtree is excluded from the sweep because its exported
  STL is stale
- **THEN** the stage emits its `stale_artifact` error and emits no achieved-range
  finding for that entry, since no sweep was performed
