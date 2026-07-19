## ADDED Requirements

### Requirement: BUILD_PLAN.json schema accepts an optional request_log
`src/build_plan_schema.json` SHALL define an optional top-level `request_log`
array. Each entry SHALL have `ts` (ISO-8601 UTC string), `kind` (one of
`initial`, `clarification`, `correction`), and non-empty `text` (verbatim user
wording), with no additional properties. When the array is present it SHALL
contain exactly one `initial` entry, and that entry SHALL be first.

#### Scenario: Plan without request_log stays valid
- **WHEN** a `BUILD_PLAN.json` without `request_log` (e.g. an eval-corpus golden
  plan) is validated
- **THEN** validation passes unchanged

#### Scenario: Well-formed log validates
- **WHEN** a plan carries `request_log` with one `initial` entry first followed by
  `clarification`/`correction` entries, each with `ts`, `kind`, and non-empty
  `text`
- **THEN** validation passes

#### Scenario: Malformed entries are rejected
- **WHEN** an entry has an unknown `kind`, empty `text`, a missing field, or an
  extra property - or the array has zero or multiple `initial` entries
- **THEN** `plan_validate.py` reports a schema validation error

### Requirement: Planning populates the initial request verbatim
The planning phase SHALL populate `request_log` when emitting a new plan: the
user's original request as the `initial` entry, plus one entry per clarification
gathered during requirements/planning, all verbatim.

#### Scenario: Fresh plan from a clarified request
- **WHEN** the planner emits `BUILD_PLAN.json` after asking two clarifying
  questions
- **THEN** the plan's `request_log` holds the original request as `initial` and
  the two answers as `clarification` entries, in order, verbatim

### Requirement: Mid-build clarifications are appended, never rewritten
When the user gives a clarification or correction after the plan is written, the
system SHALL append a dated entry to `request_log` and SHALL NOT edit, reorder,
or remove existing entries. When a correction triggers re-planning, the
regenerated plan SHALL carry the prior `request_log` forward verbatim with the
new entry appended.

#### Scenario: Correction during the part loop
- **WHEN** the user corrects a dimension while parts are being built
- **THEN** a `correction` entry with the user's wording is appended to
  `request_log` in `BUILD_PLAN.json`, and all prior entries are unchanged

#### Scenario: Re-plan preserves history
- **WHEN** a correction causes the planner to regenerate the plan
- **THEN** the new `BUILD_PLAN.json` contains every prior `request_log` entry
  unchanged, followed by the correction entry
