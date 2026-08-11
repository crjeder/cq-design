## MODIFIED Requirements

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

Because `placement` is supplied by the part author during the build phase (see
`assembled-pose-handback`), the axis arm SHALL be authoritative only on a validation run
made after the placements are in the plan -- the pre-export re-validation. On a run where
the moving union's part carries no `placement`, the validator SHALL NOT treat the
untransformed block axis as an assembled-frame result: it SHALL report the axis arm as
deferred for that entry, as a non-fatal advisory finding alongside the existing
thin-block findings, and SHALL NOT emit a `joint_contract` error from it.

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

#### Scenario: Planning-time validation defers the axis arm
- **WHEN** the plan is validated at the end of the planning phase and the moving union's
  part carries no `placement` yet
- **THEN** the validator reports the axis arm as deferred for that entry as a non-fatal
  advisory, emits no `joint_contract` error, and validation passes

#### Scenario: Pre-export validation is authoritative
- **WHEN** the plan is validated again after every part's placement write-back
- **THEN** the axis arm is evaluated against the author-supplied placements and any
  mismatch fails validation before export
