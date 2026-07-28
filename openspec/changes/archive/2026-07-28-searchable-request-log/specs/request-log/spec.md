## ADDED Requirements

### Requirement: request_log is the sole record of round-by-round history
The system SHALL treat `request_log` as the only place round-by-round build history
(per-round corrections, superseded values, "what changed since the last attempt") is
recorded. `planning_notes`, per-part `part_notes`, and generated part-script comments
SHALL NOT contain a round-by-round changelog narrative (e.g. "ROUND 2", "SUPERSEDED by
round N below"); each SHALL describe only the current design state as of the present
plan/script.

#### Scenario: Correction narrative goes to request_log, not part_notes
- **WHEN** a part's geometry changes between build attempts due to a user correction
- **THEN** the correction is appended to `request_log` as a `correction` entry, and the
  part's `part_notes` is updated (or left as-is) to describe only the part's current
  design -- it does not gain a new dated paragraph describing the prior attempt

#### Scenario: Superseded part_notes content is deleted, not annotated
- **WHEN** a round of changes makes part of `part_notes` no longer true of the current
  design
- **THEN** that content is removed from `part_notes` rather than kept and marked
  "SUPERSEDED by round N"
