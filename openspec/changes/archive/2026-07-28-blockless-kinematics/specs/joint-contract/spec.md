## MODIFIED Requirements

### Requirement: A declared joint is satisfied only when the block's dof covers it

For each `kinematics` entry that names a `block` and whose `type` is `revolute` or
`prismatic`, the plan validator SHALL verify that the referenced block's `dof` (the
reality) covers the plan's declared joint (the wish). The contract has three arms --
**type**, **axis**, and **range** -- and the joint is satisfied only when all three
hold. Any arm that fails SHALL emit a structured issue of type `joint_contract`
naming the joint, the failing arm, and the conflicting block and plan values. This
replaces the prior check that compared only `unit`. The check SHALL run without
loading any mesh. A `kinematics` entry that omits `block` (a block-less,
directly-declared joint) is out of this contract's scope by construction -- there
is no block `dof` to compare against, so the plan validator SHALL NOT apply the
type, axis, or range arms to it and SHALL NOT emit a `joint_contract` issue for it;
the entry's axis and range are taken as author-declared and correct.

#### Scenario: Type mismatch is rejected
- **WHEN** a `kinematics` entry declares `type: "revolute"` but its `block` has `dof.type:
  "spherical"`
- **THEN** the validator emits a `joint_contract` error naming the joint and both types, and the
  plan does not validate

#### Scenario: Matching single-axis joint with aligned axis and in-range motion passes
- **WHEN** a `kinematics` entry's `type` equals the block's `dof.type`, its assembled axis matches
  the block's placement-transformed `dof` axis, and its `required_range` lies within the block's
  `mechanical_limit`
- **THEN** the validator emits no `joint_contract` issue for that joint

#### Scenario: A block-less entry is out of the contract's scope by construction
- **WHEN** a `kinematics` entry omits `block`
- **THEN** the plan validator does not apply the type, axis, or coaxiality arms to
  that entry and emits no `joint_contract` issue for it, regardless of what
  `axis_dir`/`type`/`required_range` it declares
