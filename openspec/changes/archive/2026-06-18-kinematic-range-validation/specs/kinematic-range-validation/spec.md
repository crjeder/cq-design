## ADDED Requirements

### Requirement: Joint blocks declare a degree-of-freedom descriptor in the inventory

A joint entry in `blocks/inventory.json` SHALL carry a `dof` object describing its
intrinsic degree of freedom when it participates in motion validation. The `dof`
object SHALL have `type` (one of `revolute`, `prismatic`, `spherical`, `fixed`),
`axis` (one of `X`, `Y`, `Z`, the block's local motion axis), `mechanical_limit`
(a two-element `[lo, hi]` array giving the block's nominal full range), and `unit`
(`deg` for `revolute`/`spherical`, `mm` for `prismatic`). The unit SHALL be
encoded in the separate `unit` field, never in the field name. The
`mechanical_limit` is a nominal sanity bound and SHALL NOT be treated as the
authoritative achievable range for a specific instance.

#### Scenario: Revolute joint declares a degree range
- **WHEN** a hinge block declares `dof`
- **THEN** its `type` is `revolute`, its `unit` is `deg`, and its
  `mechanical_limit` is a two-element array such as `[0, 180]`

#### Scenario: Prismatic joint declares a millimetre range
- **WHEN** a sliding (dovetail) block declares `dof`
- **THEN** its `type` is `prismatic`, its `unit` is `mm`, and its
  `mechanical_limit` expresses travel in millimetres

#### Scenario: Non-joint and flexure blocks omit dof
- **WHEN** a block has no rigid degree of freedom (a non-joint primitive, or a
  `living_hinge` flexure)
- **THEN** the block omits the `dof` descriptor and is not subject to kinematic
  validation

---

### Requirement: The build plan declares required range of motion per joint

`BUILD_PLAN.json` SHALL support an optional top-level `kinematics` array. Each
entry SHALL declare `joint_id`, `moving_part` (a part id), `fixed_part` (a part
id), `block` (the joint block name), `axis_origin_mm` (a three-element world-space
point `[x, y, z]`), `axis_dir` (one of `X`, `Y`, `Z`), `type` (the joint type),
`required_range` (a two-element `[lo, hi]` array the design depends on), `unit`
(`deg` or `mm`), and `step` (the sweep increment in the same unit). The plan
`unit` SHALL match the referenced block's `dof.unit`.

#### Scenario: Plan declares a partial required range
- **WHEN** a phone-holder hinge must fold from upright to flat
- **THEN** its `kinematics` entry declares `required_range: [0, 90]` and
  `unit: "deg"`, even though the block's mechanical limit is larger

#### Scenario: Plan without kinematics skips the stage
- **WHEN** a plan has no `kinematics` array or an empty one
- **THEN** the kinematic validation stage does not run and emits no findings

---

### Requirement: Required range is checked against the block mechanical limit

For each `kinematics` entry, the stage SHALL verify the declared `required_range`
lies within the referenced block's `dof.mechanical_limit`. When the required range
falls outside the mechanical limit, the stage SHALL emit an issue of type
`range_exceeds_limit` carrying the requested range, the mechanical limit, and the
unit. This check SHALL run without loading any mesh.

#### Scenario: Required range within limit passes the numeric check
- **WHEN** `required_range` is `[0, 90]` and `mechanical_limit` is `[0, 180]`
- **THEN** no `range_exceeds_limit` issue is emitted

#### Scenario: Required range exceeds limit is flagged
- **WHEN** `required_range` is `[0, 270]` and `mechanical_limit` is `[0, 180]`
- **THEN** the stage emits a `range_exceeds_limit` issue reporting both ranges and
  does not need to load any STL to do so

---

### Requirement: The moving part is swept through the required range against the fixed part

For each `kinematics` entry whose numeric check passes, the stage SHALL load the
exported STLs of `moving_part` and `fixed_part`, then step the moving part through
`required_range` in increments of `step` (always including both endpoints), and at
each step test collision between the transformed moving part and the fixed part
using an in-process trimesh collision manager backed by fcl. For a `revolute`
joint the per-step transform SHALL be a rotation by the step value about the line
through `axis_origin_mm` in direction `axis_dir`; for a `prismatic` joint it SHALL
be a translation along `axis_dir`. The sweep SHALL be bounded to `required_range`
and SHALL NOT sweep the full `mechanical_limit`.

#### Scenario: Collision-free range passes
- **WHEN** the moving part clears the fixed part at every swept step across the
  full required range
- **THEN** the stage reports the joint as passing and emits no collision issue

#### Scenario: Binding within the range is reported
- **WHEN** the moving part is collision-free up to some angle and collides before
  reaching the end of the required range
- **THEN** the stage emits a `motion_collision` issue reporting the binding value
  (the first swept step at which collision occurs) and the required end value

#### Scenario: Only the required range is swept
- **WHEN** `required_range` is `[0, 90]` and `mechanical_limit` is `[0, 180]`
- **THEN** the sweep tests steps only across `0..90` and does not evaluate any
  position beyond 90

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
