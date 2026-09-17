## Why

`skill/phase3_build.md`'s Implementation audit step, on `verdict: fail`, has the main
session hand-type a `telemetry.py append` call with `prompt_chars=<chars>` and
`model=<builder model>` filled in by reading a prompt file's length and recalling which
model built the part. Both values are already derivable from files on disk
(`build/<part_id>_prompt_attempt<N>.txt` and `skill_config.json`'s `models.part_author`,
via the existing `part_author_model()` helper) the same way `record_attempt` derives them
for the hook's base record. Hand-typing invites drift (stale prompt_chars, wrong model
name) and adds a step the audit-fail path doesn't need.

## What Changes

- Add an `audit-fail` subcommand to `src/telemetry.py`: `telemetry.py audit-fail --part
  <part_id> --audit <path to auditor's JSON output>`.
- The subcommand reads the auditor's `verdict`/`failed_questions` JSON, finds the
  part's latest attempt number already in `attempts.jsonl`, derives `prompt_chars` from
  the matching prompt file (same lookup `record_attempt` already does), derives `model`
  via `part_author_model()` (reused from `render_prompt.py`), and appends one follow-up
  record with `outcome: "fail"`, `error_types: ["visual_mismatch"]`, and
  `visual_review: {"passed": false, "failed_question": <first failed question>}`.
- Update `skill/phase3_build.md`'s Implementation audit step to call `audit-fail` instead
  of hand-assembled `--field` flags.

## Capabilities

### Modified Capabilities
- `attempt-telemetry`: adds a dedicated audit-fail append path (`audit-fail` subcommand)
  that derives `prompt_chars` and `model` from disk instead of requiring the caller to
  supply them, for the existing visual-review-failure follow-up record.

## Impact

- `src/telemetry.py`: new `audit-fail` subcommand and its argument parsing; imports
  `part_author_model` from `render_prompt.py`.
- `skill/phase3_build.md`: Implementation audit step's command changes.
- `tests/test_telemetry.py`: new coverage for the subcommand.
