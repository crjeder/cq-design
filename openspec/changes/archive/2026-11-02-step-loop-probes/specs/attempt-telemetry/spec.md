## MODIFIED Requirements

### Requirement: Per-attempt telemetry record
An attempt SHALL be one plan revision of a part: attempt 1 is the initial plan, and each
`request_log` entry targeting the part, or a plan change at escalation, starts the next
attempt. Step runs within an attempt SHALL NOT be attempts; they SHALL be recorded in
`build/<part_id>.steps.jsonl`. `build/attempts.jsonl` SHALL carry, for every attempt,
at least one line recording `ts` (ISO 8601 UTC), `part_id`, `attempt` (1-based),
`outcome` (`pass` or `fail`), `error_types` (list of typed error names from
the wrapper/gate contract and the step report, empty on pass), `step_runs` (number of
step-worker runs in this attempt), `visual_review` (object with `passed` and
`failed_question`, or null when review did not run or has not yet been folded in),
`prompt_chars` (approximate rendered prompt size in characters, when available), and
`model` (model name, `"inline"` when no routing is in effect). A `(part_id, attempt)`
pair MAY be represented by more than one line, appended at different times as more is
learned about that attempt; the last such line in file order is authoritative for that
attempt's `outcome`, `error_types`, and `visual_review`.

#### Scenario: Failed attempt is logged with its error types
- **WHEN** a part attempt fails with wrapper errors of type `silent_boolean`
  and `thin_interface`
- **THEN** one line is appended to `build/attempts.jsonl` with `outcome: "fail"`
  and `error_types: ["silent_boolean", "thin_interface"]`

#### Scenario: Passing attempt is logged
- **WHEN** a part attempt passes validation on attempt 3
- **THEN** one line is appended with `attempt: 3`, `outcome: "pass"`, and
  `error_types: []`

#### Scenario: Step failures stay inside one attempt
- **WHEN** a builder has five failing step runs and then passes, with no plan change
- **THEN** `build/attempts.jsonl` has attempt 1 with `outcome: "pass"` and
  `step_runs: 6`, and the five failures are in `build/<part_id>.steps.jsonl`

#### Scenario: Plan change starts a new attempt
- **WHEN** a part blocked with `probe_stuck` is resumed after a plan change
- **THEN** its next record has `attempt: 2`

#### Scenario: Blocked attempt is logged with its error types
- **WHEN** an attempt ends `blocked` with `probe_stuck`
- **THEN** one line is appended with `outcome: "fail"` and `error_types` containing
  `probe_stuck`

#### Scenario: Visual review failure records the question
- **WHEN** an attempt passes geometry validation but fails visual review on a
  checklist question
- **THEN** a follow-up line for the same `part_id`/`attempt` has
  `outcome: "fail"`, `error_types: ["visual_mismatch"]`,
  `visual_review.passed: false`, and `visual_review.failed_question`
  identifying that question, and is the authoritative line for that attempt

#### Scenario: Visual review passing needs no follow-up line
- **WHEN** an attempt passes geometry validation and visual review
- **THEN** the base record already carries `outcome: "pass"` and no follow-up
  line is required
