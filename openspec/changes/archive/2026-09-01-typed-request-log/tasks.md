## 1. Schema

- [x] 1.1 Add optional `level` (`enum: ["functional","operation","parameter"]`) and
  `targets` (`type: array`, `minItems: 1`, `items: {type: string, minLength: 1}`)
  to the `request_log` items object in `src/build_plan_schema.json`; update the
  `request_log` description to mention both fields are optional and independent.
- [x] 1.2 In `tests/test_plan_validate.py`: add cases for an entry with valid
  `level`+`targets`, a mixed typed/untyped array, and rejection of unknown
  `level`, empty `targets`, empty-string `targets` item, and `targets` as a
  non-array.
- [x] 1.3 Run `uv run pytest tests/test_plan_validate.py` -- green.

## 2. Search

- [x] 2.1 In `src/request_log_search.py`: add keyword-only `level` and `target`
  params to `search_request_log` (`level` exact match on `entry.get("level")`;
  `target` case-insensitive substring against any string in
  `entry.get("targets") or []`); AND with existing filters.
- [x] 2.2 Add `--level` (choices: functional/operation/parameter) and `--target`
  (free string) argparse args wired into the call.
- [x] 2.3 In `tests/test_request_log_search.py`: cover `--level` (incl. entries
  with no `level` excluded), `--target` (part-id and `part.feature` match, no
  `targets` excluded), and combined-filter AND.
- [x] 2.4 Run `uv run pytest tests/test_request_log_search.py` -- green.

## 3. Planning prompt

- [x] 3.1 In `prompts/planning.md` rule 14: instruct setting `level` and `targets`
  on each new entry, with the three `level` definitions
  (functional/operation/parameter) and the `targets` naming convention
  (part ids + `part.feature`/parameter names); state the `initial` entry MAY omit
  both and carried-forward entries are never back-filled.

## 4. Phase 3 orchestration doc

- [x] 4.1 In `skill/phase3_build.md` "Request log" > Appending: add `level` +
  `targets` to the entry shape the orchestrator writes, with the same
  definitions as the planning prompt.
- [x] 4.2 Add the parameter-scope routing rule: an entry with `level: "parameter"`
  is applied only to literals in the parts named in its `targets`; a value shared
  across parts routes through `joints` / `mate_chain.py`, never a duplicated
  literal in an untargeted sibling.
- [x] 4.3 In "Request log" > Searching: mention `--level` / `--target` as
  narrowing options alongside `--kind`.
- [x] 4.4 In the Step 3 section-selection block: change the interface<->entry
  match from the `--query "<name>"` substring to `targets` membership
  (`name` or `<part>.<name>` in the entry's `targets`), keeping the
  `--query` substring only as the fallback for entries with no `targets`;
  tiers stay `kind`-based.

## 5. Spec sync + validation

- [x] 5.1 Run `openspec validate typed-request-log` -- passes.
- [x] 5.2 Run the fast test subset
  (`uv run pytest tests/test_plan_validate.py tests/test_request_log_search.py`)
  -- green.
- [x] 5.3 Grep `prompts/`, `skill/`, `reference/` for stale "`--query`"-only
  descriptions of the section matcher and reconcile.
