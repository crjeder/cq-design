## 1. `src/log.py`

- [x] 1.1 Create `src/log.py` with a top-level subparser tree: `journal append
      <journal> <milestone> <text>`, `attempt append <file> [json] [--hook]`,
      `attempt audit-fail --part <id> --audit <path>`, `request search <plan>
      [--query] [--kind] [--level] [--target]`, `request add <plan> --kind
      <kind> --text <text> [--level] [--target]...`
- [x] 1.2 Move `journal.py`'s `append_line` into `log.py` unchanged; wire to
      `journal append`
- [x] 1.3 Move `telemetry.py`'s append/validate/hook logic, `fold_attempts`,
      and `part_author_model` into `log.py` unchanged; wire to `attempt append`
- [x] 1.4 Move `telemetry.py`'s `audit-fail` logic into `log.py` unchanged;
      wire to `attempt audit-fail`
- [x] 1.5 Move `request_log_search.py`'s search/add logic into `log.py`
      unchanged; wire to `request search` / `request add`
- [x] 1.6 Delete `src/journal.py`, `src/telemetry.py`, `src/request_log_search.py`

## 2. `src/plan.py`

- [x] 2.1 Create `src/plan.py` with a top-level subparser tree: `validate
      <plan> [existing plan_validate.py flags]`, `summary <plan>`,
      `import-params <script> --part <id> [--plan] [--write]`
- [x] 2.2 Move `plan_validate.py`'s `validate_plan` and all validation logic
      into `plan.py` unchanged; wire to `validate`
- [x] 2.3 Move `plan_summary.py`'s logic into `plan.py` unchanged; wire to
      `summary`
- [x] 2.4 Move `import_params.py`'s logic into `plan.py` unchanged; wire to
      `import-params`
- [x] 2.5 Delete `src/plan_validate.py`, `src/plan_summary.py`, `src/import_params.py`

## 3. Repoint in-process imports

- [x] 3.1 `src/quality_gate.py`: `_run_plan_validation_stage` imports
      `validate_plan` from `plan` instead of `plan_validate`
- [x] 3.2 `src/render_prompt.py`: import `fold_attempts` and
      `part_author_model` from `log` instead of `telemetry`
- [x] 3.3 `grep -rn "import plan_validate\|from plan_validate\|import telemetry\|from telemetry\|import journal\|from journal\|import request_log_search\|from request_log_search\|import plan_summary\|from plan_summary\|import import_params\|from import_params" src/ tests/` and confirm every hit is accounted for in this task group

## 4. Permissions

- [x] 4.1 In `src/skill_permissions.json`, remove the six Bash + six
      PowerShell allow-pattern pairs for the replaced scripts (both the
      `uv run --project * python * <script>.py *` and bare `python *
      <script>.py *` forms where present) and add one Bash + one PowerShell
      pair each for `log.py *` and `plan.py *`
- [x] 4.2 Update the sentinel comment/value if it referenced a replaced
      script (check `_comment` and `sentinel` keys)

## 5. Tests

- [x] 5.1 Merge `tests/test_journal.py`, `tests/test_telemetry.py`,
      `tests/test_request_log_search.py` into `tests/test_log.py`, updating
      imports and CLI invocations to the new subcommand paths
- [x] 5.2 Merge `tests/test_plan_validate.py`, `tests/test_plan_summary.py`,
      `tests/test_import_params.py` into `tests/test_plan.py`, updating
      imports and CLI invocations to the new subcommand paths
- [x] 5.3 Delete the six superseded test files
- [x] 5.4 Run `uv run pytest tests/test_log.py tests/test_plan.py
      tests/test_quality_gate.py tests/test_render_prompt.py` and fix any
      failures

## 6. Docs and prompts

- [x] 6.1 `reference/scripts.md`: replace the six per-script entries with two
      entries for `log.py` and `plan.py`, each documenting all of their
      subcommands
- [x] 6.2 `SKILL.md`, `skill/*.md`, `prompts/*.md`: update every example
      invocation of the six replaced scripts to the new subcommand form
- [x] 6.3 `CLAUDE.md`'s script index: replace the six entries with two
- [x] 6.4 `grep -rn "journal\.py\|telemetry\.py\|request_log_search\.py\|plan_validate\.py\|plan_summary\.py\|import_params\.py" SKILL.md skill/ prompts/ reference/ CLAUDE.md` and confirm zero remaining hits

## 7. Spec corpus cosmetic updates

- [x] 7.1 In each of the ~15 spec files listed in `proposal.md`'s Impact
      section (`openspec/specs/<name>/spec.md`), replace the literal mention
      of a replaced script's invocation with its `log.py`/`plan.py`
      subcommand form. This is a direct text edit to the existing spec files,
      not a delta spec under this change, since no requirement's behavior
      changes
- [x] 7.2 `grep -rln "journal\.py\|telemetry\.py\|request_log_search\.py\|plan_validate\.py\|plan_summary\.py\|import_params\.py" openspec/specs/` and confirm zero remaining hits (archived changes under `openspec/changes/archive/` are historical and excluded from this check)

## 8. Final verification

- [x] 8.1 `uv run pytest tests/` (full suite)
- [x] 8.2 `uv run python evals/run_evals.py` (score-only, no `--generate`) to
      confirm no case's pipeline invocation broke
- [x] 8.3 `openspec validate cluster-log-plan-scripts --strict`
