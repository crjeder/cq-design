## ADDED Requirements

### Requirement: Audit-fail follow-up command
`src/telemetry.py` SHALL provide an `audit-fail --part <part_id> --audit <path>`
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
- **WHEN** `audit-fail --part lid --audit build/lid_audit.json` is run, `attempts.jsonl`
  already has a `part_id: "lid"`, `attempt: 2` record from the hook, a prompt file
  `build/lid_prompt_attempt2.txt` exists, `skill_config.json` sets
  `models.part_author` to `claude-sonnet-5`, and the audit JSON has
  `"verdict": "fail"` and `"failed_questions": ["Does the lid seat flush?"]`
- **THEN** a follow-up line is appended with `part_id: "lid"`, `attempt: 2`,
  `outcome: "fail"`, `error_types: ["visual_mismatch"]`, `model: "claude-sonnet-5"`,
  `prompt_chars` equal to the length of `build/lid_prompt_attempt2.txt`, and
  `visual_review: {"passed": false, "failed_question": "Does the lid seat flush?"}`

#### Scenario: No prior attempt for the part is an error
- **WHEN** `audit-fail --part lid --audit build/lid_audit.json` is run but
  `attempts.jsonl` has no record for `part_id: "lid"`
- **THEN** the command exits non-zero and appends nothing

#### Scenario: Audit JSON with no failed questions is an error
- **WHEN** the audit JSON at `<path>` has `"failed_questions": []`
- **THEN** the command exits non-zero and appends nothing

### Requirement: Shared model resolution helper
`part_author_model()` (resolving `models.part_author` from `./skill_config.json`,
falling back to the seeded default, else `"unknown"`) SHALL live in
`src/telemetry.py` so both the `audit-fail` subcommand and `render_prompt.py` share
one implementation; `render_prompt.py` SHALL import it from `telemetry.py` rather
than defining its own copy.

#### Scenario: render_prompt and audit-fail agree on the resolved model
- **WHEN** `skill_config.json` sets `models.part_author` to `claude-opus-5`
- **THEN** both `render_prompt.py`'s validate-args rendering and
  `telemetry.py audit-fail`'s derived `model` field resolve to `claude-opus-5`
