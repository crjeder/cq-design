## Context

`request_log` (spec `request-log`) preserves the user's wording verbatim but
gives it no structure. Two documented failures follow from that:

- The C5 cradle ping-pong: a dimension shared by two parts was corrected for one
  and hand-edited into the other's script, so later rounds kept re-diverging.
- Every gate downstream of Phase 2 audits parts against `BUILD_PLAN.json`, never
  against the request, so a Phase 2 misreading becomes the standard the pipeline
  enforces.

`TODO.md` (Intent-recognition survey) picks this as the smallest change with the
largest reach: it reuses the append-only log, its schema, `plan_validate.py`'s
`_check_request_log`, and `request_log_search.py`. Strategy: reimplement
LLM4CAD-Editor's functional/operation/parameter intent levels.

## Goals / Non-Goals

**Goals:**
- Each new `request_log` entry carries an intent `level` and the `targets` it
  names, assigned at append time.
- The C5 failure class is expressible as a written rule keyed on `level` +
  `targets`.
- `request_log_search.py` can filter by `level` and `targets`.
- Phase 3 Step 3 section-selection tiering keys off `targets` instead of a
  keyword match, with a fallback for untyped entries.
- Existing plans (including eval-corpus goldens) with untyped entries stay valid.

**Non-Goals:**
- No validator that diffs part scripts to enforce the parameter-scope rule; it
  stays orchestrator discipline.
- No back-filling of `level`/`targets` onto entries in a carried-forward log.
- No change to `_check_request_log` (the one-`initial`-entry-first rule).
- The remaining Intent-recognition survey items (spec-audit categories,
  request-relative acceptance, canonical restatement, under-specified evals) are
  separate changes.

## Decisions

### Decision 1: `level` is a closed enum, `targets` is a flat string array

`level`: `functional` | `operation` | `parameter`, matching LLM4CAD-Editor.
`targets`: `array` of non-empty strings, `minItems: 1`, each either a bare part
id (`"cradle"`) or a dotted `part.feature` / parameter name
(`"cradle.saddle_width"`). No sub-objects, no separate `parts` / `features`
keys.

*Alternative considered:* `targets` as `{parts: [...], features: [...]}`. Rejected
-- the search filter and the section-matcher both want a single membership test;
a flat list gives it with a substring check and no shape to keep in sync.

### Decision 2: Both fields optional, enforced only in the JSON Schema

`request_log` items are `additionalProperties: false`, so `level` and `targets`
are added as optional properties with `enum` / `minItems` + item constraints.
`_check_request_log` in `plan_validate.py` is untouched. Draft-7 `enum` and
`minItems` cover every malformed case; nothing needs a Python-side check the way
the single-`initial` rule did.

*Alternative considered:* make them required for `kind != "initial"`. Rejected --
breaks every existing plan and every eval golden, contradicting the TODO's
"must stay valid" constraint.

### Decision 3: Parameter-scope rule lives in `skill/phase3_build.md`, not code

The rule -- "a `parameter` entry applies only to literals in its `targets`;
route a shared value through `joints` / `mate_chain.py`" -- needs a script-level
diff to enforce mechanically, which is disproportionate. It is written as
orchestrator discipline next to the existing append rule, and as a spec
requirement (`request-log`: "A parameter-level entry is applied only within its
targets") so an eval can check the behavior later.

### Decision 4: Section-matcher prefers `targets`, falls back to `--query`

`preview-cross-sections`' ranking requirement keeps its three `kind`-based tiers.
Only the match test changes: an interface matches a `request_log` entry when its
`name` (or `<part>.<name>`) is in the entry's `targets`; for an entry with no
`targets`, fall back to the existing `request_log_search.py --query "<name>"`
substring match. This keeps older/untyped plans working with no tiering change.

### Decision 5: `search_request_log` gains two keyword-only params

`search_request_log(plan, *, query=None, kind=None, level=None, target=None)`.
`level` is an exact match against `entry.get("level")`; `target` is a
case-insensitive substring against any string in `entry.get("targets") or []`.
CLI adds `--level` (choices) and `--target` (free string). All filters AND, as
today.

## Risks / Trade-offs

- **Planner/orchestrator mis-types an entry** (e.g. a shape change labeled
  `parameter`) -> the parameter-scope rule then wrongly constrains it. Mitigation:
  `level` definitions in the prompt are explicit about "the design is otherwise
  fixed"; the rule only blocks cross-part literal edits, which is the safe
  default regardless.
- **`targets` drift from actual part ids** (a typo'd part name) -> the
  section-matcher silently misses. Mitigation: same failure mode as today's
  substring miss; falls through to tier 3, not a hard error.
- **Two representations for the same match during transition** (`targets` vs
  text) -> tier assignment could differ mid-corpus. Accepted: the fallback is
  only reached for entries with no `targets`, so a single plan is internally
  consistent per entry.

## Migration Plan

1. Schema + `plan_validate` tests (no behavior change for untyped plans).
2. `request_log_search.py` filters + tests.
3. `prompts/planning.md` rule 14 and `skill/phase3_build.md` append/search/Step-3
   text.
4. Spec deltas archived with the change.

No rollback concern: every field is additive and optional; reverting the schema
change only makes newer typed plans fail validation, so revert would also revert
the writers.

## Open Questions

- Should the `initial` entry be encouraged to carry a coarse `functional` level +
  the full part-id list, or left untyped? Current spec: MAY omit both. Leaving it
  to the planner prompt to recommend, not the schema.
