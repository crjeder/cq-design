## Context

Three fields currently accumulate free-text content that looks like it should be
history, but only one is designed for it:

- `request_log` (top-level array): append-only, verbatim, one entry per user request/
  clarification/correction, `{ts, kind, text}`. Purpose-built for round-by-round history
  (`openspec/specs/request-log/spec.md`), validated by `plan_validate.py::_check_request_log`.
- `planning_notes` (top-level string): "LLM design reasoning: part decomposition choices,
  material decisions, dimension sources" per the schema description.
- `part_notes` (per-part string): "LLM reasoning for this part: blocks chosen, geometry
  written from scratch, unusual decisions" per the schema description.

Nothing in the prompts or schema descriptions tells the LLM that `planning_notes`/
`part_notes` are current-state-only. In practice (`TODO.md`'s C5 Phone-Holder
retrospective) `part_notes` grew a full "ROUND 2..7" changelog -- duplicating both
`request_log` and the part script's own comments -- because nothing said not to.
Separately, `src/build_plan_schema.json` and `prompts/planning.md` each define/state
`request_log` twice (a literal duplicate-key bug, not a design choice), and there is no
way to query `request_log` without loading the whole array into context.

## Goals / Non-Goals

**Goals:**
- One place (`request_log`) for round-by-round build/correction history; `planning_notes`
  and `part_notes` hold only a description of the current state.
- Fix the schema's and the planning prompt's literal duplicate-`request_log` bug.
- A stdlib-only tool to search `request_log` by keyword/kind so a correction round doesn't
  need the full array in context.

**Non-Goals:**
- Changing `plan_validate.py`'s enforcement mechanism (the manual initial-first-entry
  check stays; this change doesn't try to express that constraint declaratively in the
  draft-7 schema).
- Retrofitting existing `BUILD_PLAN.json` files that already have changelog-style
  `part_notes`/`planning_notes` -- this is prompt/schema guidance for new and re-planned
  builds, not a migration script.
- Redoing the wording/condensation pass already scoped in the not-yet-applied
  `condense-planning-prompt` change (merging the duplicate rule-14 text, renumbering).
  That change and this one touch overlapping lines in `prompts/planning.md`'s
  `request_log` rule; this change adds semantic content (the exclusivity prescription),
  not a rewrite of the surrounding prose.
- A `--part` filter on `request_log` search: entries have no part association today
  (`{ts, kind, text}` only); adding one is a schema change out of scope here. `--kind`
  and `--query` (substring on `text`) are sufficient for "don't read the whole file."

## Decisions

**Schema dedup, not schema redesign.** `src/build_plan_schema.json` defines the
top-level `request_log` property twice: once at (current) lines 51-57 using
`items`/`additionalItems` against `$ref`'d tuple definitions (`request_log_initial_entry`/
`request_log_followup_entry`), and again at lines 247-260 with an inline `items` schema
and a prose note about the initial-first constraint. Since a JSON object can't have two
keys with the same name, any parser (including the `jsonschema` library this project
uses) keeps whichever key survives the parse -- in practice the second one, since Python's
`json.load` keeps the last occurrence of a duplicate key. The first definition's tuple
validation was never actually enforced. Decision: keep one definition (the second,
simpler one, since it's the one already in effect) and delete the first, along with the
now-unused `request_log_initial_entry`/`request_log_followup_entry` definitions if
nothing else references them. No behavior changes -- `plan_validate.py`'s manual check is
unaffected either way.

**Exclusivity is prompt/schema-description guidance, not a new validator.** There is no
reliable way to detect "this part_notes reads like a changelog" mechanically. This change
is a documentation/prompt fix: update the schema's field `description`s and the relevant
prompt/skill-doc prose to state the rule plainly, matching how the project already
handles similar guidance (e.g. rule 13's `cq_gears` pointer is prose-only, no schema
enforcement).

**Search tool: filter-and-print, not an index.** `request_log` arrays are small (tens of
entries even in a 7-round retrospective) compared to, say, a source file -- the problem
isn't search performance, it's that today the only interface is "read the whole
`BUILD_PLAN.json` file," which pulls in every other field (parts, blocks_needed,
constraints, etc.) just to look at a handful of log entries, and re-injects the growing
array into the model's context on every reference. A linear substring/kind filter over
the array, printing only matches, solves the actual problem. No new index file, no
separate storage -- `request_log` in `BUILD_PLAN.json` stays the single source of truth.
Follows the existing small-stdlib-tool pattern (`script_lint.py`, `telemetry.py`):
stdlib + `json` only, CLI entry point, importable function for programmatic use.

**Where the search tool is invoked from.** `skill/phase3_build.md`'s existing "Request
log" section (append-only writes) gets a paired "read" instruction: when Phase 3 needs
prior context on a specific feature/decision during Escalation or a correction round, it
runs `request_log_search.py` with a keyword instead of re-reading `BUILD_PLAN.json`'s
full log. `prompts/part.md` is not the injection point for `request_log` today (only
`part_notes`/`interfaces`/etc. are templated in) and stays that way -- the search tool is
a main-session/orchestrator-level lookup, not a per-part-prompt placeholder.

## Risks / Trade-offs

[Two openspec changes edit the same `request_log` rule text in `prompts/planning.md`
concurrently] -> Called out explicitly in the proposal; this change's tasks describe the
semantic addition in terms of content, not fixed line/rule numbers, so it applies cleanly
whichever change lands first. If `condense-planning-prompt` lands first, this change's
task is to add the exclusivity sentence to whatever the merged rule is numbered.

[Deleting the schema's first `request_log` definition could be perceived as removing
tuple-position validation] -> That validation was never actually active (dead due to the
duplicate key), so nothing observable changes; `tests/test_plan_validate.py` should still
pass unchanged as confirmation.

[Prose-only exclusivity guidance can still drift] -> No stronger enforcement is proposed
here (see Non-Goals); if drift recurs, a future change could add a lint check (e.g. flag
`part_notes` containing "ROUND" or multiple dated entries) similar to `script_lint.py`'s
static checks.

## Migration Plan

No data migration. Existing `BUILD_PLAN.json` files with changelog-style `part_notes`
keep working (schema still accepts a string); the guidance only shapes newly generated or
re-planned content. Roll out is a single-commit prompt/schema/tool change; rollback is
reverting that commit.

## Open Questions

- Should `request_log` entries eventually carry an optional part/feature tag to make
  filtering more precise? Deferred (see Non-Goals) -- revisit if `--query`/`--kind`
  filtering proves too coarse in practice.
