## MODIFIED Requirements

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
