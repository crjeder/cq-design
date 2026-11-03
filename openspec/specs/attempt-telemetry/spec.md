# attempt-telemetry Specification

## Purpose

Record one append-only JSON line per part-script attempt in `build/attempts.jsonl`, so failure
patterns, attempt counts, and prompt costs are measurable across sessions -- the baseline every
prompt, reference, or model-routing change is judged against.
## Requirements
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

### Requirement: Telemetry append helper
The system SHALL provide `src/log.py` with an append function and an `attempt append`
CLI subcommand that validates a record against the attempt schema, stamps `ts` when
absent, and appends it as a single well-formed JSON line. Invalid records SHALL be
rejected with a non-zero exit code and SHALL NOT write a partial line.
`src/log.py` SHALL also provide a `fold_attempts(records) -> list[dict]`
helper that groups records by `(part_id, attempt)` and returns one record per
group — the last record in input order — for use by any consumer that scores
or checks the log, and a `--hook` entry point that reads a Claude Code
`PostToolUse` payload from stdin, derives a base record's fields from the
observed `run_cadquery_model.py` invocation and its result, and appends it
using the same validated-append path as the CLI.

#### Scenario: Valid record appended via CLI
- **WHEN** the `attempt append` CLI is invoked with a record containing the required
  fields
- **THEN** exactly one parseable JSON line is appended to the target file and
  the process exits 0

#### Scenario: Invalid record rejected
- **WHEN** the `attempt append` CLI is invoked with a record missing `part_id`
- **THEN** the process exits non-zero and the target file is unchanged

#### Scenario: Unknown extra keys are preserved
- **WHEN** a record includes a key not in the schema (e.g. `phase`)
- **THEN** the record is accepted and the extra key appears in the appended line

#### Scenario: Fold keeps the last record per attempt
- **WHEN** `fold_attempts` is given two records sharing `part_id: "housing"`,
  `attempt: 2` — the first with `outcome: "pass"` and `visual_review: null`,
  the second with `outcome: "fail"` and a populated `visual_review` — plus one
  unrelated record for `attempt: 1`
- **THEN** it returns two records: `attempt: 1` unchanged, and `attempt: 2`
  equal to the second (later) `attempt: 2` record

#### Scenario: Hook derives and appends a base record
- **WHEN** the `--hook` entry point receives a `PostToolUse` payload for a
  `run_cadquery_model.py` Bash call whose `--script` argument is
  `build/housing.py` and whose tool result JSON has `success: false` and
  `errors: [{"type": "thin_interface", ...}]`
- **THEN** one record is appended with `part_id: "housing"`,
  `attempt` computed from the existing log, `outcome: "fail"`,
  `error_types: ["thin_interface"]`, and `visual_review: null`

#### Scenario: Hook is a no-op when it cannot resolve the target
- **WHEN** the `--hook` entry point receives a payload whose command does not
  match the `run_cadquery_model.py` shape, or whose working directory has no
  `build/` yet
- **THEN** it exits 0 and appends nothing

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
The quality gate SHALL check for a per-attempt telemetry log and, after
folding it with `fold_attempts`, emit a `warning` finding (`source:
"telemetry"`, `type: "telemetry_missing"`) when the folded log is absent,
empty, or contains no parseable JSON record. The finding SHALL NOT be an
`error`: an unwritten log never blocks delivery, since the geometry it would
have described is unaffected.

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

#### Scenario: A base-plus-follow-up pair is not double-reported
- **WHEN** `attempts.jsonl` holds two lines for the same `part_id`/`attempt`
  (a base record and its visual-review follow-up)
- **THEN** the gate's folded view treats them as one attempt and emits no
  `telemetry_missing` finding

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

### Requirement: Audit-fail follow-up command
`src/log.py` SHALL provide an `attempt audit-fail --part <part_id> --audit <path>`
subcommand that appends the visual-review-failure follow-up record for `part_id`
without requiring the caller to supply `prompt_chars` or `model`. It SHALL read the
auditor's JSON output at `<path>` (the `verdict`/`failed_questions`/`findings`/
`missing_views` contract rendered by `render_prompt.py audit`), resolve the target
attempt as the highest `attempt` already recorded for `part_id` in `attempts.jsonl`
(via `fold_attempts`), derive `prompt_chars` from the same prompt-file lookup
`record_attempt` uses for that attempt, derive `model` via `part_author_model()`, and
append one record with `outcome: "fail"`, `error_types: ["visual_mismatch"]`, and
`visual_review: {"passed": false, "failed_question": <first entry of
failed_questions>}`.

#### Scenario: Audit-fail appends a derived follow-up record
- **WHEN** `log.py attempt audit-fail --part lid --audit build/lid_audit.json` is run,
  `attempts.jsonl` already has a `part_id: "lid"`, `attempt: 2` record from the hook, a
  prompt file `build/lid_prompt_attempt2.txt` exists, `skill_config.json` sets
  `models.part_author` to `claude-sonnet-5`, and the audit JSON has
  `"verdict": "fail"` and `"failed_questions": ["Does the lid seat flush?"]`
- **THEN** a follow-up line is appended with `part_id: "lid"`, `attempt: 2`,
  `outcome: "fail"`, `error_types: ["visual_mismatch"]`, `model: "claude-sonnet-5"`,
  `prompt_chars` equal to the length of `build/lid_prompt_attempt2.txt`, and
  `visual_review: {"passed": false, "failed_question": "Does the lid seat flush?"}`

#### Scenario: No prior attempt for the part is an error
- **WHEN** `log.py attempt audit-fail --part lid --audit build/lid_audit.json` is run
  but `attempts.jsonl` has no record for `part_id: "lid"`
- **THEN** the command exits non-zero and appends nothing

#### Scenario: Audit JSON with no failed questions is an error
- **WHEN** the audit JSON at `<path>` has `"failed_questions": []`
- **THEN** the command exits non-zero and appends nothing

### Requirement: Shared model resolution helper
`part_author_model()` (resolving `models.part_author` from `./skill_config.json`,
falling back to the seeded default, else `"unknown"`) SHALL live in
`src/log.py` so both the `attempt audit-fail` subcommand and `render_prompt.py` share
one implementation; `render_prompt.py` SHALL import it from `log.py` rather
than defining its own copy.

#### Scenario: render_prompt and audit-fail agree on the resolved model
- **WHEN** `skill_config.json` sets `models.part_author` to `claude-opus-5`
- **THEN** both `render_prompt.py`'s validate-args rendering and
  `log.py attempt audit-fail`'s derived `model` field resolve to `claude-opus-5`

