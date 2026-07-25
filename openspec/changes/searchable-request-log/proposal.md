## Why

The pipeline has grown three overlapping places for round-by-round history: `request_log`
(designed for exactly this -- see `openspec/specs/request-log/spec.md`), `part_notes`, and
`planning_notes`. Nothing stops the latter two from turning into a changelog: the C5
Phone-Holder retrospective (`TODO.md`, "plan bloat" sub-item) found a part's `part_notes`
carrying ~6KB of "ROUND 2..7" narrative that mostly duplicated `request_log` and the
script's own comments, feeding straight into the plan-injection token-bloat problem
`TODO.md` already tracks. Separately, `src/build_plan_schema.json` defines the top-level
`request_log` property twice (lines 51-57 and 247-260) -- a JSON object can't have a
duplicate key, so the second silently wins and the first (with its tuple-shaped
`items`/`additionalItems` validation) is dead weight; `prompts/planning.md` has the same
duplication, with two rules both numbered 14 that each restate the `request_log`
population rule. And even where `request_log` is used correctly, the only way to recall
why a past decision was made is to re-read the entire array into context -- there is no
way to search it by keyword, kind, or part.

## What Changes

- Dedupe `src/build_plan_schema.json`'s `request_log` property definition to one
  definition (the one `plan_validate.py`'s `_check_request_log` actually relies on for the
  initial-first check; the schema itself keeps `additionalProperties: false` on entries).
- Prescribe `request_log` as the **exclusive** place for round-by-round build history
  (per-round corrections, superseded values, "what changed and why between attempts").
  `planning_notes` and `part_notes` describe the CURRENT design state only; a superseded
  round's rationale gets deleted when superseded, never appended as "SUPERSEDED by round
  N below". Generated part-script comments follow the same rule (current-state rationale
  only, no round-history narrative) -- this is an application of the project's existing
  no-changelog-comment convention (`CLAUDE.md`'s comment rules), not a new one.
- Add `src/request_log_search.py`: a stdlib-only CLI/importable helper that filters
  `BUILD_PLAN.json`'s `request_log` by substring (`--query`, matched against `text`,
  case-insensitive) and/or `--kind`, printing only matching entries as JSON. This gives
  Phase 3 (and any correction-round reasoning) a way to recall relevant prior history
  without re-reading the whole array into context, the same way `script_lint.py` is a
  small stdlib tool the pipeline shells out to rather than reasoning over raw source.
- Wire the search tool into `skill/phase3_build.md`'s "Request log" section and
  `prompts/part.md` (or the relevant escalation-handling text) so a correction round
  searches instead of re-reading the full plan/log.
- Update `CLAUDE.md`'s Core Scripts table with the new script.

This change's wording edits to `prompts/planning.md`'s `request_log` rule overlap with
the not-yet-applied `condense-planning-prompt` change (which also merges the duplicate
rule-14 pair, as a pure wording/token-count pass). This change adds new semantic content
(the notepad-exclusivity prescription) to whichever rule number that merge produces;
apply order between the two is a sequencing decision for the user, not a conflict in what
either one requires.

## Capabilities

### New Capabilities
- `request-log-search`: a stdlib-only script that searches `BUILD_PLAN.json`'s
  `request_log` by keyword/kind instead of requiring the full array to be read into
  context.

### Modified Capabilities
- `request-log`: dedupe the schema's duplicate `request_log` property definition; add a
  requirement that `request_log` is the exclusive place for round-by-round history (not
  `planning_notes`/`part_notes`).
- `planning-phase`: add a requirement that `planning_notes` and `part_notes` describe
  current design state only, never a round-by-round changelog, and cross-reference
  `request_log` as where that history belongs instead.

## Impact

- `src/build_plan_schema.json` -- remove the duplicate `request_log` property.
- `src/request_log_search.py` (new), `tests/test_request_log_search.py` (new).
- `prompts/planning.md`, `prompts/part.md`, `skill/phase2_planning.md`,
  `skill/phase3_build.md` -- notepad-exclusivity wording + search-tool usage.
- `CLAUDE.md` -- Core Scripts table entry for the new script.
- `TODO.md` -- mark the "plan bloat: part_notes doubled as changelog" sub-item (under the
  C5 Phone-Holder retrospective item) as addressed by this change.
- No change to `plan_validate.py`'s enforcement logic (the manual initial-first check is
  kept as the single enforcement mechanism); `tests/test_plan_validate.py` should still
  pass unchanged.
