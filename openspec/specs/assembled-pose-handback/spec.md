# assembled-pose-handback Specification

## Purpose

Defines the planner-to-author pose contract: a part's `placement` is authored by
whichever agent actually built the geometry, not by the planner that positioned the
part before that geometry existed. The planner declares the assembled pose as intent
-- a goal a reader can check against a render -- and the part author, free to choose
whatever frame suits the geometry, reports the assembled-frame transform that carries
its authored geometry into that stated pose. The plan is re-validated after every
part's handback and before export, because checks that consume `placement` (such as
the joint-contract axis arm) are only authoritative once every part has reported its
transform.

## Requirements

### Requirement: The planner declares the assembled pose as intent, not as a transform

A part MAY carry an optional `pose_intent` (string): the part's goal pose in the shared
assembled frame, stated in terms a reader can check against a render -- which way the
part faces and where it sits in the model. `pose_intent` SHALL NOT restate a rotation
sequence or translation vector; the structured form of the pose is `placement`.

The planner SHALL NOT author `parts[].placement`. A `placement` present in a plan the
planner did not write (a prior plan, a hand-edited plan) SHALL remain valid and SHALL be
treated by the part author as a proposal to confirm or correct, not as an error.

#### Scenario: Planner states a pose goal
- **WHEN** the planner places a wall panel upright at a corner of the model
- **THEN** the part carries a `pose_intent` such as "stands upright, outward face toward
  world -Y, at the NE corner" and no `placement`

#### Scenario: Pose intent does not restate the transform
- **WHEN** a `pose_intent` would otherwise describe "rotated +90 deg about X then yawed
  90 deg about Z, translated to (16.35, 169.35, 0)"
- **THEN** it states the goal pose instead, and the rotation sequence appears only in the
  author-supplied `placement`

#### Scenario: A pre-existing planner-written placement still validates
- **WHEN** a plan written before this change declares `parts[].placement`
- **THEN** validation passes unchanged and the part author treats that placement as its
  starting proposal

### Requirement: The part author chooses its authoring frame and returns the placement

The part author SHALL be free to author the part's geometry in whatever frame suits the
geometry, and SHALL report the assembled-frame transform for the frame it chose by
writing `parts[].placement` back into `BUILD_PLAN.json` after the part is accepted. The
returned `placement` SHALL carry the part's authored geometry into the pose stated by
`pose_intent`.

The write-back SHALL follow the same principle already applied to `dimensions` and
`load`: a corrected understanding is written into the plan, not held only in the
session. An absent `placement` after the write-back SHALL continue to mean identity, per
`printable-unit-model`.

#### Scenario: Author builds in a different frame than a proposed placement assumed
- **WHEN** a part carries a proposed `placement` that assumes the panel was authored
  lying flat, and the author instead authors it standing upright
- **THEN** the author writes back the `placement` that positions its own upright
  geometry, replacing the proposal

#### Scenario: Author builds directly in the assembled frame
- **WHEN** the authored geometry already sits in the pose `pose_intent` describes
- **THEN** the author leaves `placement` absent, which means identity

#### Scenario: A multi-union part returns one placement
- **WHEN** one part script produces several unions in one authored frame
- **THEN** the author returns the single `placement` that applies to all of that part's
  unions

#### Scenario: A mate-chained part returns no placement
- **WHEN** a part's pose is derived through a `joints` mate chain from `root_part`
- **THEN** the author writes back no `placement` for it, because its pose is derived

### Requirement: The part prompt carries the pose intent to the author

`prompts/part.md` SHALL include a `{{POSE_INTENT}}` substitution carrying the part's
`pose_intent` (or an explicit "none" marker when absent), and SHALL state the author's
obligation to report the assembled-frame transform as an enumerated contract rule.
`skill/phase3_build.md`'s substitution table SHALL define the placeholder's value, in
both the cold (builder agent) and inline (progressive) render modes.

#### Scenario: Part prompt renders the pose intent
- **WHEN** a part declares `pose_intent`
- **THEN** the rendered part prompt contains that text, in both cold and inline modes

#### Scenario: Part with no declared pose intent
- **WHEN** a part declares no `pose_intent`
- **THEN** the placeholder renders an explicit "none" marker rather than being dropped
  silently

### Requirement: The plan is re-validated after the last handback and before export

After the final part's `placement` write-back and before `model_export.py` runs,
`plan.py validate` SHALL be run again against `BUILD_PLAN.json`. That run SHALL be the
authoritative validation for any check that consumes `placement`, including the
joint-contract axis arm. A failure SHALL block the export.

#### Scenario: Re-validation catches a handback that breaks the joint contract
- **WHEN** an author returns a `placement` that rotates a joint block's `dof` axis away
  from the plan's declared `axis_dir`
- **THEN** the pre-export validation run fails with a `joint_contract` error and the
  export does not proceed

#### Scenario: Clean re-validation proceeds to export
- **WHEN** every part's write-back is complete and validation passes
- **THEN** model export runs
