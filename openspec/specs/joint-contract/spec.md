# joint-contract Specification

## Purpose

Define the mesh-free contract check that verifies a build plan's declared joint (the
wish) is actually realisable by the referenced block's degree of freedom (the reality).
The check compares joint type, axis (in the assembled frame, after placement), and
required range for `revolute` and `prismatic` joints, emitting structured
`joint_contract` issues when any arm fails. Spherical joints are out of scope pending a
future model.

## Requirements

### Requirement: A declared joint is satisfied only when the block's dof covers it

For each `kinematics` entry whose `type` is `revolute` or `prismatic`, the plan validator SHALL
verify that the referenced block's `dof` (the reality) covers the plan's declared joint (the wish).
The contract has three arms -- **type**, **axis**, and **range** -- and the joint is satisfied only
when all three hold. Any arm that fails SHALL emit a structured issue of type `joint_contract`
naming the joint, the failing arm, and the conflicting block and plan values. This replaces the
prior check that compared only `unit`. The check SHALL run without loading any mesh.

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

### Requirement: The joint axis is matched in the assembled frame after placement

The validator SHALL compare the plan's assembled-frame axis against the block's `dof` axis
expressed in block coordinates and pushed through the moving union's `placement` (rotations then
translation) into the assembled frame. The comparison rule depends on the joint type:

- A `revolute` joint SHALL be **coaxial**: the transformed `dof.direction` SHALL be parallel (up to
  sign) to the plan's `axis_dir`, AND the plan's `axis_origin_mm` SHALL lie on the transformed axis
  line (through the transformed `dof.origin` in the transformed `dof.direction`).
- A `prismatic` joint SHALL be **parallel**: the transformed `dof.direction` SHALL be parallel (up
  to sign) to the plan's `axis_dir`; the axis position is unconstrained, because translation along
  any parallel line is the same motion.

Direction parallelism and point-on-line tests SHALL use a fixed numeric tolerance. A mismatch SHALL
emit a `joint_contract` issue identifying the joint and the conflicting axes.

#### Scenario: Revolute axis off-line is rejected
- **WHEN** a `revolute` joint's `axis_dir` is parallel to the block's transformed axis but its
  `axis_origin_mm` does not lie on the transformed axis line
- **THEN** the validator emits a `joint_contract` error reporting the joint is not coaxial

#### Scenario: Prismatic parallel axis at a different position passes
- **WHEN** a `prismatic` joint's `axis_dir` is parallel to the block's transformed slide direction
  but its `axis_origin_mm` is offset from the block's axis line
- **THEN** the validator emits no axis `joint_contract` issue, because parallel direction alone
  satisfies a prismatic joint

#### Scenario: Axis honors the union placement
- **WHEN** a block authored with `dof.direction` along block-Y is placed by a `placement` that
  rotates it 90 degrees so its axis points along assembled-Z, and the plan declares `axis_dir: "Z"`
- **THEN** the axis arm passes, because the block axis is compared after the placement transform

### Requirement: Spherical joints are not contract-checked

The contract check SHALL apply only to `revolute` and `prismatic` joints. A `kinematics` entry whose
`type` (or whose block `dof.type`) is `spherical` SHALL be skipped by the contract check and SHALL
NOT emit a `joint_contract` issue, pending a future spherical joint model. Ball blocks retain their
`dof` unchanged.

#### Scenario: Spherical joint produces no contract finding
- **WHEN** a `kinematics` entry references a `ball_socket`/`ball_stud` block with `dof.type:
  "spherical"`
- **THEN** the contract check emits no `joint_contract` issue for that joint
