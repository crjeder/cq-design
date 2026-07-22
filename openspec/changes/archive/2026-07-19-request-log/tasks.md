## 1. Schema

- [x] 1.1 Add the optional `request_log` property to `src/build_plan_schema.json`:
  entry object `{ts, kind, text}`, `additionalProperties: false`, `kind` enum,
  non-empty `text`; exactly-one-`initial`-first constraint (contains/prefixItems
  or a small check in `plan_validate.py` if draft-7 cannot express it cleanly)
- [x] 1.2 Extend `tests/test_plan_validate.py`: plan without the field passes;
  well-formed log passes; unknown kind, empty text, extra property, missing
  field, zero/duplicate `initial`, and non-first `initial` each fail

## 2. Prompt and skill rules

- [x] 2.1 Add the planning.md rule: populate `request_log` verbatim (initial
  request + Phase 1/2 clarifications); on re-plan, carry the existing log forward
  and append
- [x] 2.2 Add the SKILL.md rule: append a dated entry per mid-build
  clarification/correction; never edit, reorder, or remove existing entries

## 3. Verify

- [x] 3.1 Run `uv run pytest tests/test_plan_validate.py` and the eval-corpus
  sanity test (`tests/test_eval_corpus.py`) to confirm golden plans still validate
- [x] 3.2 Update the CLAUDE.md `plan_validate.py` row if the exactly-one-initial
  check lands in code rather than schema (n/a: the check landed entirely in the
  schema's tuple `items`/`additionalItems`, no new code path in `plan_validate.py`)
