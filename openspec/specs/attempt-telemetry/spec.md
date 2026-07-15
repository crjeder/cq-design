# attempt-telemetry Specification

## Purpose

Record one append-only JSON line per part-script attempt in `build/attempts.jsonl`, so failure
patterns, attempt counts, and prompt costs are measurable across sessions -- the baseline every
prompt, reference, or model-routing change is judged against.

## Requirements

### Requirement: Per-attempt telemetry record
The part loop SHALL append exactly one JSON line to `build/attempts.jsonl` for
every part-script attempt, recording at minimum: `ts` (ISO 8601 UTC), `part_id`,
`attempt` (1-based), `outcome` (`pass` or `fail`), `error_types` (list of typed
error names from the wrapper/gate contract, empty on pass), `visual_review`
(object with `passed` and `failed_question`, or null when review did not run),
`prompt_chars` (approximate rendered prompt size in characters), and `model`
(model name, `"inline"` when no routing is in effect).

#### Scenario: Failed attempt is logged with its error types
- **WHEN** a part attempt fails with wrapper errors of type `silent_boolean`
  and `thin_interface`
- **THEN** one line is appended to `build/attempts.jsonl` with `outcome: "fail"`
  and `error_types: ["silent_boolean", "thin_interface"]`

#### Scenario: Passing attempt is logged
- **WHEN** a part attempt passes validation on attempt 3
- **THEN** one line is appended with `attempt: 3`, `outcome: "pass"`, and
  `error_types: []`

#### Scenario: Visual review failure records the question
- **WHEN** an attempt passes geometry validation but fails visual review on a
  checklist question
- **THEN** the appended record has `visual_review.passed: false` and
  `visual_review.failed_question` identifying that question

### Requirement: Telemetry append helper
The system SHALL provide `src/telemetry.py` with an append function and CLI
that validates a record against the attempt schema, stamps `ts` when absent,
and appends it as a single well-formed JSON line. Invalid records SHALL be
rejected with a non-zero exit code and SHALL NOT write a partial line.

#### Scenario: Valid record appended via CLI
- **WHEN** the CLI is invoked with a record containing the required fields
- **THEN** exactly one parseable JSON line is appended to the target file and
  the process exits 0

#### Scenario: Invalid record rejected
- **WHEN** the CLI is invoked with a record missing `part_id`
- **THEN** the process exits non-zero and the target file is unchanged

#### Scenario: Unknown extra keys are preserved
- **WHEN** a record includes a key not in the schema (e.g. `phase`)
- **THEN** the record is accepted and the extra key appears in the appended line

### Requirement: Append-only log semantics
`build/attempts.jsonl` SHALL be append-only across attempts and sessions: the
helper SHALL never truncate, rewrite, or reorder existing lines, and SHALL
create the file (and `build/`) on first append.

#### Scenario: Log survives across sessions
- **WHEN** a new session appends an attempt record to an existing
  `build/attempts.jsonl`
- **THEN** all previously written lines remain byte-identical and the new
  record is the last line

#### Scenario: First append creates the file
- **WHEN** the helper appends and neither `build/` nor `attempts.jsonl` exists
- **THEN** both are created and the file contains exactly the one record
