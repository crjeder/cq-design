## MODIFIED Requirements

### Requirement: User corrections are applied to the generated plan
If the user provides a corrected value for any dimension during the checkpoint review, the skill SHALL use the corrected value when generating `BUILD_PLAN.json`, not the looked-up value.

The skill SHALL write `parameters.py` in the caller's working directory as soon as the
user approves or corrects the table -- before Phase 2 starts -- recording every
dimension in the table with its corrected value, source, and status as a comment. This
is the durable record of the checkpoint's research; deferring it to Phase 2 loses it if
the session is interrupted between the two. Phase 2 updates the same file only when
planning introduces or changes a measurement.

#### Scenario: User corrects a value inline
- **WHEN** the user says "the depth should be 8.5, not 8.0"
- **THEN** the plan uses 8.5 mm for that dimension

#### Scenario: User approves without changes
- **WHEN** the user confirms the table is correct
- **THEN** the plan uses all looked-up values as presented

#### Scenario: Provenance written at approval

- **WHEN** the user approves the dimension table
- **THEN** `parameters.py` is written in the same turn, and a journal milestone is
  appended, before the planning prompt is rendered

#### Scenario: Session interrupted after approval

- **WHEN** the session is cut off after the table is approved but before
  `BUILD_PLAN.json` exists
- **THEN** `parameters.py` holds every approved dimension and its source, so the
  resumed session re-runs no web lookups
