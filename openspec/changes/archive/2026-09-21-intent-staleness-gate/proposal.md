## Why

`BUILD_PLAN.json`'s approved `intent` is the pipeline's statement of what the user
agreed to build, and every downstream consumer -- the Phase 3 request-conformance bar,
Phase 4's `REGENERATE.md`, the planner on a re-plan -- treats it as current. But the rule
that keeps it current ("rewrite `intent` on each approved correction") is prose in
`skill/phase3_build.md` with nothing checking it. When the orchestrator appends a
`correction` to `request_log` and forgets the rewrite, `intent` silently describes a
design that no longer exists, and the acceptance bar built on it starts measuring renders
against a superseded reading. `skill/phase4_deliver.md` already names this failure mode as
a known cause of a wrong `REGENERATE.md` -- it is a reproduced defect with no gate.

This is the remaining open half of TODO's "User intent as an invariant over generation
loops": capture shipped (`approved-intent`), the per-part bar shipped
(`request-relative-acceptance`), but nothing mechanically holds `intent` and `request_log`
in sync, so intent is still a convention rather than an invariant.

## What Changes

- `BUILD_PLAN.json` gains an optional `intent_ts` field: the ISO-8601 UTC timestamp of the
  newest `request_log` entry that `intent` has been reconciled against. It records
  acknowledgement, not edit -- a correction that legitimately changes nothing about the
  design still advances `intent_ts` while leaving `intent` untouched.
- `plan_validate.py` gains a blocking check: if `request_log` carries any
  `clarification`/`correction` entry whose `ts` is newer than `intent_ts` (or if
  `intent_ts` is absent while such entries exist), the plan fails validation with a message
  naming the unreconciled entries. Plans with no non-`initial` entries -- the common
  single-round case and every eval golden but one -- are unaffected and need no
  `intent_ts`.
- Because the quality gate already runs `plan_validate.validate_plan` and maps its errors
  to `plan_invalid`, the check reaches the gate with no change to `gate-plan-validation`.
- `request_log_search.py add` gains `--reconciled`, which stamps `intent_ts` to the entry
  it just appended, for the case where the orchestrator has already rewritten `intent` (or
  determined no rewrite is needed) in the same turn. It is deliberately opt-in: an
  unflagged `add` leaves the plan failing validation until the intent is dealt with, which
  is the enforcement.
- `skill/phase3_build.md`'s correction-handling rule and `skill/phase1_requirements.md`'s
  exit checkpoint state the stamp as part of writing/rewriting `intent`.
- **BREAKING** for plans that carry unreconciled non-`initial` `request_log` entries: they
  now fail validation until `intent_ts` is added. One eval golden
  (`evals/cases/lid-thickness-correction/BUILD_PLAN.json`) is affected and is updated in
  this change.

## Capabilities

### New Capabilities

_None. The stamp is the enforcement mechanism for an existing `approved-intent`
requirement, not a separate capability._

### Modified Capabilities

- `approved-intent`: the current-state rewrite requirement gains its mechanical half --
  the `intent_ts` reconciliation stamp written alongside the approved text in Phase 1 and
  advanced on every approved correction (including one that changes nothing), and the
  validator rule that fails a plan whose `request_log` has moved past it.

## Impact

- `src/build_plan_schema.json` -- new optional top-level `intent_ts`
- `src/plan_validate.py` -- new blocking `check_intent_reconciled`, wired into
  `validate_plan`
- `src/request_log_search.py` -- `add --reconciled` flag
- `skill/phase1_requirements.md`, `skill/phase3_build.md` -- stamp stated in the write and
  rewrite rules
- `tests/test_plan_validate.py`, `tests/test_request_log_search.py` -- new cases
- `evals/cases/lid-thickness-correction/BUILD_PLAN.json` -- golden gains `intent_ts`
- `TODO.md` -- "Intent as invariant" details updated with what remains after this change
