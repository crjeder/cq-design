## MODIFIED Requirements

### Requirement: The build plan declares required range of motion per joint

`BUILD_PLAN.json` SHALL support an optional top-level `kinematics` array. Each
entry SHALL declare `joint_id`, `moving_union` (the id of the union that moves),
`block` (the joint block name), `axis_origin_mm` (a three-element world-space point
`[x, y, z]` in assembled coordinates), `axis_dir` (one of `X`, `Y`, `Z`), `type`
(the joint type), `required_range` (a `[lo, hi]` range the design depends on,
**relative to the block's authored pose**, which is the zero point), `unit` (`deg`
or `mm`), and `step` (the sweep increment in the same unit). `required_range` MAY be
negative and MAY straddle zero (e.g. `]-30, 90]`), and SHALL carry per-bound
inclusivity following mathematical interval notation (an open bound need not be
reached; a closed bound must be cleared; default closed/closed). The fixed set SHALL
be derived as every other union in the model and SHALL NOT be enumerated in the
entry. The plan `unit` SHALL match the referenced block's `dof.unit`.

#### Scenario: Plan declares a moving union and a partial required range
- **WHEN** a phone-holder arm union must fold from upright to flat
- **THEN** its `kinematics` entry declares `moving_union`, `required_range: [0, 90]`,
  and `unit: "deg"`, and the fixed set is every other union in the model

#### Scenario: Plan without kinematics skips the stage
- **WHEN** a plan has no `kinematics` array or an empty one
- **THEN** the kinematic validation stage does not run and emits no findings

---

### Requirement: The moving union is swept through the required range against the rest of the model

For each `kinematics` entry whose numeric check passes, the stage SHALL load the
moving union's assembled mesh and the assembled meshes of every other union in the
model, then step the moving union through `required_range` in increments of `step`
(relative to the authored-pose zero, including each closed bound and excluding each
open bound), and at each step test collision between the transformed moving union
and the fixed set. The fixed set SHALL be added as **separate named collision
objects** (one per non-moving union), not a single merged mesh, so the binding union
can be identified. Collision SHALL be tested with an in-process trimesh collision
manager backed by fcl. For a `revolute` joint the per-step transform SHALL be a
rotation by the step value about the line through `axis_origin_mm` in direction
`axis_dir`; for a `prismatic` joint it SHALL be a translation along `axis_dir`. The
sweep SHALL run in assembled (use) coordinates, SHALL be bounded to
`required_range`, and SHALL NOT sweep the full `mechanical_limit`. A
print-in-place joint whose unions share one plate SHALL be validated the same way,
using its per-union meshes; it SHALL NOT be deferred or skipped for being a single
print. A `motion_collision` issue SHALL name the colliding union so the design loop
can act on it.

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
- **WHEN** the moving union clears every other union at every swept step across the
  full required range
- **THEN** the stage reports the joint as passing and emits no collision issue

#### Scenario: Print-in-place joint is checked, not deferred
- **WHEN** both leaves of a print-in-place hinge are two unions sharing one plate
- **THEN** the stage sweeps the moving leaf union against the fixed leaf union (and
  any other unions) and reports binding or pass, rather than skipping the joint

#### Scenario: Only the required range is swept
- **WHEN** `required_range` is `[0, 90]` and `mechanical_limit` is `[0, 180]`
- **THEN** the sweep tests steps only across `0..90` and does not evaluate any
  position beyond 90
