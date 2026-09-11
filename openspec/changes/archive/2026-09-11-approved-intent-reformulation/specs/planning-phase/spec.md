## ADDED Requirements

### Requirement: Planning consumes the approved intent rather than authoring it

The planning phase SHALL treat the approved reformulation Phase 1 wrote to `intent` as
input: it SHALL copy that text into the emitted `BUILD_PLAN.json`'s `intent` unchanged,
and SHALL plan the part decomposition against it. The planner SHALL NOT author `intent`
from scratch, and SHALL NOT paraphrase or shorten the approved text.

When a re-plan regenerates the file, the planner SHALL carry the current approved
`intent` forward unchanged, the same way it carries `request_log` forward. Only an
approved correction rewrites `intent` (see the `approved-intent` spec).

#### Scenario: Planner copies the approved intent

- **WHEN** Phase 1 exits with an approved reformulation and the planner is invoked
- **THEN** the emitted `BUILD_PLAN.json` carries that text verbatim as `intent`

#### Scenario: Re-plan preserves the approved intent

- **WHEN** a correction causes the planner to regenerate the plan
- **THEN** the new `BUILD_PLAN.json` carries forward the current approved `intent`, and
  the planner does not rewrite it

#### Scenario: Plan contradicts the approved intent

- **WHEN** the decomposition the planner produces would build something the approved
  `intent` does not describe
- **THEN** the planner revises the decomposition to match the approved intent rather than
  editing `intent` to match the decomposition

### Requirement: Plan validation rejects a token intent

The `BUILD_PLAN.json` schema SHALL require `intent` to be long enough to carry a
reformulation rather than a token phrase, so that a plan whose `intent` was never
replaced by the Phase 1 approved text fails validation.

The `-1` unresolved-dimension placeholder needs no additional validator rule: every
size-valued numeric field in the schema (`parts[].dimensions.*`,
`interfaces[].diameter_mm`, `interfaces[].size_mm[]`, `blocks_needed[].extents_mm[]`,
`kinematics.step`) already carries `exclusiveMinimum: 0` and rejects it. The schema's
remaining unbounded numeric fields are signed by design -- `interfaces[].position_mm`,
`load.dir`, `show_face.dir`, `placement.translate_mm`, `placement.rotate[].angle_deg`,
`kinematics.axis_origin_mm`, `kinematics.required_range`, `kinematics.mechanical_limit`
-- where `-1` is a legitimate value. A blanket `-1` rejection SHALL NOT be added, as it
would reject valid plans.

#### Scenario: Token intent is rejected

- **WHEN** a plan's `intent` is shorter than the reformulation floor
- **THEN** `plan_validate.py` reports a schema validation error for `intent`

#### Scenario: Unresolved dimension is already rejected

- **WHEN** a part's `dimensions.d_mm` is `-1`
- **THEN** validation fails on the existing `exclusiveMinimum: 0` bound, naming that
  field

#### Scenario: A legitimate negative value still validates

- **WHEN** a part declares `load.dir` of `[0, 0, -1]` and an interface at
  `position_mm` `[-12.5, 0, 4]`
- **THEN** validation passes -- no rule rejects `-1` in a signed field
