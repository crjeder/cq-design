## 1. Refactor model resolution into telemetry.py

- [x] 1.1 Move `part_author_model()` from `src/render_prompt.py` into `src/telemetry.py`
- [x] 1.2 Update `src/render_prompt.py` to import `part_author_model` from `telemetry`
  instead of defining it, and drop the now-unused inline copy

## 2. Add the audit-fail subcommand

- [x] 2.1 Add a shared prompt-file-length helper (extracted from `record_attempt`'s
  existing glob loop) so `record_attempt` and `audit-fail` use one implementation
- [x] 2.2 Add `audit_fail(attempts_log, part_id, audit_path)` that: reads and
  JSON-parses `audit_path`; errors if `failed_questions` is missing/empty; resolves the
  target attempt as the max attempt for `part_id` via `fold_attempts` on the existing
  log, erroring if none exists; derives `prompt_chars` via the shared helper for that
  attempt; derives `model` via `part_author_model()`; builds and appends the record via
  `append_attempt`
- [x] 2.3 Wire an `audit-fail` argparse subcommand (`--part`, `--audit`) in `main()`
  that calls `audit_fail` and maps its errors to a non-zero exit with a stderr message,
  matching the existing `append` subcommand's error-handling style

## 3. Update the phase 3 skill doc

- [x] 3.1 Replace skill/phase3_build.md's Implementation audit step-3 `telemetry.py
  append --field ...` block with the new `telemetry.py audit-fail --part <part_id>
  --audit <path to auditor's JSON output>` command

## 4. Tests

- [x] 4.1 `tests/test_telemetry.py`: audit-fail appends a correctly derived record
  (happy path from the spec's first scenario)
- [x] 4.2 `tests/test_telemetry.py`: audit-fail errors and appends nothing when there is
  no prior attempt for the part
- [x] 4.3 `tests/test_telemetry.py`: audit-fail errors and appends nothing when the
  audit JSON's `failed_questions` is empty
- [x] 4.4 `tests/test_render_prompt.py`: existing `part_author_model` coverage still
  passes against the imported version (update the import path if the test patches the
  module-local name directly) — no such test exists (grep confirmed), nothing to update
