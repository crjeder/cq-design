## 1. Schema

- [x] 1.1 Add optional top-level `intent_ts` (type `string`) to `src/build_plan_schema.json`, described as the ISO-8601 UTC `ts` of the newest `request_log` entry `intent` has been reconciled against -- acknowledgement, not edit; absent on plans with no mid-build entries
- [x] 1.2 Extend the `request_log` field description to point at `intent_ts` as its reconciliation pair

## 2. Validator

- [x] 2.1 Add `check_intent_reconciled(plan)` to `src/plan_validate.py`: returns errors for each `clarification`/`correction` entry whose `ts` is strictly newer than `intent_ts`, and one error when such entries exist with `intent_ts` absent
- [x] 2.2 Parse timestamps with `datetime.fromisoformat` after rewriting a trailing `Z` to `+00:00`; return an error naming any unparseable `ts`/`intent_ts` instead of comparing it
- [x] 2.3 Wire the check into `validate_plan`'s error list (not the advisory findings block), so the standalone CLI exits 1 and the quality gate maps it to `plan_invalid` with no gate change
- [x] 2.4 Confirm no `gate-plan-validation` change is needed by running `quality_gate.py` against a plan with an unreconciled correction and checking the issue is `source: "plan"`, `type: "plan_invalid"`

## 3. Append path

- [x] 3.1 Add `--reconciled` to `request_log_search.py add`: sets `intent_ts` to the `ts` of the entry just appended, before the existing schema validation and write
- [x] 3.2 Update the module docstring and `add` help text with the flag and a usage line, stating that an unflagged `add` deliberately leaves the plan failing validation

## 4. Skill documentation

- [x] 4.1 `skill/phase1_requirements.md`: the exit checkpoint writes `intent_ts` (the `initial` entry's `ts`) alongside the approved `intent`
- [x] 4.2 `skill/phase3_build.md`: the correction-handling rule advances `intent_ts` in the same turn as the append, including for a correction that leaves `intent` unchanged; name `--reconciled` as the one-command path
- [x] 4.3 `skill/phase4_deliver.md`: replace the "check whether `intent` was never updated" prose at the `REGENERATE.md` step with a pointer to the now-enforced validator check

## 5. Tests

- [x] 5.1 `tests/test_plan_validate.py`: unreconciled correction fails; `intent_ts` equal to newest entry passes; `initial`-only and no-`request_log` plans pass without `intent_ts`; entries present with `intent_ts` absent fails; unparseable `intent_ts` fails
- [x] 5.2 `tests/test_request_log_search.py`: `add --reconciled` stamps `intent_ts` to the new entry's `ts`; `add` without it leaves `intent_ts` untouched and the resulting plan fails `validate_plan`

## 6. Corpus and docs

- [x] 6.1 Add `intent_ts` to `evals/cases/lid-thickness-correction/BUILD_PLAN.json`, set to its `correction` entry's `ts`
- [x] 6.2 Run `uv run pytest tests/test_plan_validate.py tests/test_request_log_search.py tests/test_eval_corpus.py` and confirm no other golden regresses
- [x] 6.3 Update `TODO.md`'s "Intent as invariant" details: the staleness gate closes the mechanical half; what remains is the model-level bar, blocking promotion (eval-gated), and the deferred ambiguity re-audit
- [x] 6.4 Run `ruff check --fix` and `ruff format` on the changed Python files
