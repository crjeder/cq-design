## ADDED Requirements

### Requirement: Build plan carries a review-policy preference

The build plan SHALL allow the user's review-frequency preference to be recorded
as a plan-level `review_policy` field, one of `minimal`, `checkpoints`, or
`every_stage`. Plan validation SHALL accept the field when present and SHALL
accept plans that omit it. The effective `review_policy` for a plan SHALL be its
own declared value when present, otherwise `every_stage`. The planning phase
SHALL record the policy from the user's stated review-frequency preference when
one is given, and the plan summary (see the "Plan is shown to user for review
before loop starts" requirement) SHALL surface the effective value.

`review_policy` replaces the previously informal, undeclared "run autonomously"
override as the mechanism for skipping progressive-build checkpoints -- see the
`progressive-build` spec for how the effective value selects build mode per part.

#### Scenario: Plan-level review policy validates

- **WHEN** a build plan declares `review_policy: "minimal"` at the plan level
- **THEN** plan validation accepts it and the value is available to the Phase 3
  part loop to select build mode

#### Scenario: Plan without a review policy defaults to every_stage

- **WHEN** a plan omits `review_policy` entirely
- **THEN** plan validation accepts it and the plan's effective review policy is
  `every_stage`

#### Scenario: Invalid review policy value is rejected

- **WHEN** a plan declares `review_policy` set to a value other than `minimal`,
  `checkpoints`, or `every_stage`
- **THEN** plan validation fails with an error naming the field and the invalid
  value

#### Scenario: Summary surfaces the effective review policy

- **WHEN** the plan summary is shown to the user before the orchestration loop
  starts
- **THEN** the summary states the plan's effective `review_policy`, whether
  declared explicitly or defaulted
