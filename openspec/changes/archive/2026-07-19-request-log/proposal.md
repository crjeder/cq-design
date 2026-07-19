## Why

A crashed or interrupted session is currently unrecoverable except by re-prompting
from memory: the original user request and every clarification live only in the
conversation. Improvement plan item 11 (week-1 slice) adds a verbatim `request_log`
to `BUILD_PLAN.json` while the schema is being touched, so the plan carries the
prompt history that explains it. The prompt evolves through clarifications; a
"current prompt" snapshot would lose the history - hence an append-only log.

## What Changes

- `src/build_plan_schema.json`: new optional `request_log` array. Each entry:
  `{ts, kind, text}` where `kind` is `initial | clarification | correction` and
  `text` is the user's wording verbatim. Optional so existing plans (including the
  eval-corpus golden plans) remain valid.
- `prompts/planning.md`: rule to populate `request_log` with the initial request
  (and any clarifications gathered during Phase 1/2) when emitting the plan.
- SKILL.md: rule to append a dated entry for every later clarification or
  correction the user gives mid-build - append, never rewrite or delete existing
  entries.
- Lives in the JSON, not a separate markdown file: it travels with the plan, gets
  schema-validated, and avoids a second source of truth drifting.
- Out of scope for this change: the resume procedure (re-validate from disk, skip
  passing parts) - that is the rest of item 11, scheduled later; this change only
  lands the data it will need.

## Capabilities

### New Capabilities
- `request-log`: the append-only verbatim request history in `BUILD_PLAN.json` -
  entry shape, population at planning time, and the append-on-clarification rule.

### Modified Capabilities

(none - `request_log` is an optional additive field; no existing requirement's
behavior changes. `plan_validate.py` accepts it via the schema without new
cross-checks.)

## Impact

- `src/build_plan_schema.json` (one new property), `prompts/planning.md`, SKILL.md.
- `tests/test_plan_validate.py`: cases for valid/invalid `request_log` entries.
- Existing plans and the eval corpus stay valid (field is optional).
- Foundation for the later resume-state change (rest of item 11).
