## 1. Fix the duplicate request_log definition

- [ ] 1.1 In `src/build_plan_schema.json`, delete the first top-level `request_log`
      property definition (currently lines 51-57, the one using
      `items`/`additionalItems` against `$ref`'d tuple definitions), keeping the second
      (currently lines 247-260).
- [ ] 1.2 Delete the now-unreferenced `request_log_initial_entry` and
      `request_log_followup_entry` entries under `definitions` if nothing else in the
      schema references them after 1.1.
- [ ] 1.3 Run `uv run pytest tests/test_plan_validate.py tests/test_eval_corpus.py` to
      confirm the dedup is behavior-neutral.

## 2. Build the search tool

- [ ] 2.1 Create `src/request_log_search.py` (stdlib-only, following the
      `telemetry.py`/`script_lint.py` CLI pattern): a `search_request_log(plan, *,
      query=None, kind=None)` function that loads `request_log` from a plan dict (or
      `[]` if absent), filters by case-insensitive substring match on `text` when
      `query` is given and/or exact match on `kind` when given, and returns the
      matching entries in original order.
- [ ] 2.2 Add a CLI (`argparse`) taking a `BUILD_PLAN.json` path, `--query`, and
      `--kind {initial,clarification,correction}`, printing the matching entries as a
      JSON array to stdout. Exit 0 whether or not there are matches (empty array is not
      an error); exit 1 only on a genuine error (missing file, invalid JSON).
- [ ] 2.3 Add `tests/test_request_log_search.py` (fast, no CadQuery, alongside
      `test_telemetry.py`/`test_script_lint.py`): covers keyword match, kind filter,
      combined filter, no-match empty result, and a plan with no `request_log` field.

## 3. Prescribe request_log exclusivity

- [ ] 3.1 Update `src/build_plan_schema.json`'s `planning_notes` and `part_notes`
      field `description`s to state they describe current design state only, not a
      changelog, and point to `request_log` for round history.
- [ ] 3.2 Update `prompts/planning.md`'s `request_log` rule (rule 14, or whatever it is
      numbered after the `condense-planning-prompt` change if that lands first) to add:
      `planning_notes` and per-part `part_notes` are current-state-only; round-by-round
      history goes exclusively to `request_log`.
- [ ] 3.3 Update `prompts/part.md`'s guidance on `part_notes` (and the part-script
      comment guidance, if stated there) with the same current-state-only rule, and
      state that a superseded round's rationale is deleted, not annotated "SUPERSEDED by
      round N".
- [ ] 3.4 Update `skill/phase2_planning.md`'s `planning_notes` description (the
      sentence at line ~55 distinguishing it from `parameters.py`) to also note it is
      current-state-only.
- [ ] 3.5 Update `skill/phase3_build.md`'s "Request log" section to add: when a
      correction changes a part's design, update that part's `part_notes` to reflect
      only the new current state (delete superseded content) rather than appending a
      dated round entry.

## 4. Wire the search tool into Phase 3

- [ ] 4.1 In `skill/phase3_build.md`'s "Request log" section, add a "searching" half
      alongside the existing "appending" instructions: when the orchestrator needs
      prior context on a specific decision/feature during Escalation or a correction
      round, run `python src/request_log_search.py BUILD_PLAN.json --query <keyword>`
      instead of re-reading the full `request_log` array.
- [ ] 4.2 Add `src/request_log_search.py` to `CLAUDE.md`'s Core Scripts table.

## 5. Close out

- [ ] 5.1 Update `TODO.md`: mark the "plan bloat: part_notes doubled as a full
      round-by-round changelog" sub-item (under the C5 Phone-Holder retrospective item)
      as done, referencing this change, in the same style as other completed sub-items
      in that file (e.g. "DONE via openspec change `searchable-request-log`").
- [ ] 5.2 Run the full fast test subset
      (`uv run pytest tests/test_plan_validate.py tests/test_script_lint.py
      tests/test_telemetry.py tests/test_request_log_search.py`) to confirm nothing
      regressed.
