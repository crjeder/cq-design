## Why

The `request_log` records the user's wording verbatim but assigns it no
structure, so every gate downstream of Phase 2 audits parts against the plan
rather than the request, and a shared value corrected for one part gets
hand-edited into a sibling part's script (the C5 cradle ping-pong). Typing each
entry with an intent `level` and the `targets` it names makes that failure class
expressible as a rule and gives the Phase 3 preview-section tiering a real key
instead of a keyword match.

## What Changes

- Add two OPTIONAL fields to each `request_log` entry: `level`
  (`functional` | `operation` | `parameter`, per LLM4CAD-Editor) and `targets`
  (array of non-empty strings naming affected part ids and/or
  `part.feature`/parameter names), assigned at append time.
- Existing untyped entries stay valid; absence of either field is unchanged
  behavior.
- Planning (`prompts/planning.md` rule 14) and the Phase 3 append rule
  (`skill/phase3_build.md`) instruct assigning `level` + `targets` on every new
  entry.
- New routing rule: a `parameter`-level entry MUST NOT be applied by editing a
  literal in a part it does not `target`; a value shared across parts routes
  through `joints` / `mate_chain.py`. Documented discipline in
  `skill/phase3_build.md`, not a new validator.
- `request_log_search.py` gains `--level` and `--target` filters.
- Phase 3 Step 3 preview-section tiering keys off `targets` membership instead of
  the `--query "<name>"` substring match.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `request-log`: entries gain optional `level` and `targets`; new requirement for
  the parameter-scope routing rule; planning/append requirements updated to
  populate the fields.
- `request-log-search`: search gains `level` and `target` filters.
- `preview-cross-sections`: `--extra-section` selection matches an interface to a
  `request_log` entry by `targets` membership, with the `--query` substring match
  kept only as the fallback for entries that carry no `targets`.

## Impact

- `src/build_plan_schema.json` (`request_log` items, `additionalProperties: false`)
- `src/request_log_search.py` (`search_request_log` signature + CLI)
- `prompts/planning.md` rule 14
- `skill/phase3_build.md` (append rule, Searching, Step 3 section selection)
- `openspec/specs/request-log/`, `openspec/specs/request-log-search/`,
  `openspec/specs/preview-cross-sections/`
- `tests/test_plan_validate.py`, `tests/test_request_log_search.py`
- Not touched: `src/plan_validate.py`'s `_check_request_log` (initial-entry rule
  unchanged); eval-corpus goldens (fields optional).
