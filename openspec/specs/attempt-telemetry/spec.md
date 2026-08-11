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

### Requirement: Missing telemetry detected at the gate
The quality gate SHALL check for a per-attempt telemetry log and emit a
`warning` finding (`source: "telemetry"`, `type: "telemetry_missing"`) when the
log is absent, empty, or contains no parseable JSON record. The finding SHALL
NOT be an `error`: an unwritten log never blocks delivery, since the geometry it
would have described is unaffected.

#### Scenario: Log file absent
- **WHEN** the gate runs and no `attempts.jsonl` exists at the resolved path
- **THEN** the report's `issues` include one `telemetry_missing` finding with
  severity `warning`, and `passed` is unchanged by it

#### Scenario: Log file present but empty
- **WHEN** `attempts.jsonl` exists but is zero-length or holds only blank lines
- **THEN** one `telemetry_missing` warning is emitted

#### Scenario: Log file holds no parseable record
- **WHEN** `attempts.jsonl` exists and is non-empty but no line parses as JSON
- **THEN** one `telemetry_missing` warning is emitted

#### Scenario: Populated log is silent
- **WHEN** `attempts.jsonl` holds at least one parseable JSON record
- **THEN** no telemetry finding is emitted

### Requirement: Telemetry log path resolution
The gate SHALL resolve the telemetry log to `attempts.jsonl` in the directory
holding the part scripts (the same `build/` directory the part loop appends to),
and SHALL accept an explicit override path on the CLI.

#### Scenario: Default resolution alongside the part scripts
- **WHEN** the gate is run with `--script build/lid.py` and no override
- **THEN** it checks `build/attempts.jsonl`

#### Scenario: Explicit override
- **WHEN** the gate is run with an explicit attempts-log path
- **THEN** it checks that path instead of the default

### Requirement: Missing telemetry reported at delivery
Phase 4 delivery SHALL surface a `telemetry_missing` finding to the user in the
status report, naming the log that was expected, so a session that skipped the
Step 5 appends is visible rather than silently unmeasured.

#### Scenario: Delivery with no telemetry written
- **WHEN** the gate report carries a `telemetry_missing` warning at delivery
- **THEN** the delivery status names the missing `build/attempts.jsonl` and that
  this session produced no measurement data
