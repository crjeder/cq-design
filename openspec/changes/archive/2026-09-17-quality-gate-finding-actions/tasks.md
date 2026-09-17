## 1. Action classification in quality_gate.py

- [x] 1.1 Add `_ACTION_OVERRIDE` dict and `_DEFAULT_ACTION` dict, and a
      `_classify_action(issue: dict) -> str` function to `src/quality_gate.py` per
      design.md's Decisions section.
- [x] 1.2 In `run_gate`, after `all_issues` is fully assembled (after the Gridfinity
      stage, before computing `errors`/`passed`), set `issue["action"] = _classify_action(issue)`
      on every item in `all_issues`.

## 2. Tests

- [x] 2.1 In `tests/test_quality_gate.py`, add assertions that a representative error
      finding without an override gets `action: fix`, a representative warning finding
      without an override gets `action: warn_only`, and that the report's every issue
      has an `action` key.
- [x] 2.2 Add a test (in `tests/test_quality_gate.py` or alongside the stage that emits
      it) asserting `stale_artifact` findings get `action: re_export` regardless of
      severity.
- [x] 2.3 Add a test asserting `motion_collision`, `range_exceeds_limit`, and
      `contact_limited_stop` findings get `action: ask_user`.
- [x] 2.4 Run `uv run pytest tests/test_quality_gate.py tests/test_gate_freshness.py tests/test_gate_plan_validation.py tests/test_gridfinity.py tests/test_keep_out_check.py tests/test_plate_clearance_check.py tests/test_quality_gate_parameters.py tests/test_quality_gate_telemetry.py tests/test_cosmetic_slope_gate.py`
      and fix any assertion that pins the exact issue-dict key set. (129 passed, no fixes needed)

## 3. Documentation

- [x] 3.1 Replace `skill/phase3_build.md`'s Quality gate section's per-type bullet list
      (`severity: error`, `stale_artifact`, `motion_collision`, `plate_clearance`,
      `range_exceeds_limit`, `Warnings (...)`) with the generic `action`-routing rule
      from design.md's Decisions section ("phase3_build.md replacement text").
- [x] 3.2 Re-read the whole Quality gate section afterward to confirm no other prose
      still references a finding `type` directly (e.g. the `--fix` note two lines above,
      the journal-append example) in a way that now contradicts the action-based routing.

## 4. Verification

- [x] 4.1 Run the full test suite (`uv run pytest tests/`) to confirm nothing else
      asserts the old issue-dict shape. (931 passed, 1 pre-existing skip)
- [x] 4.2 Grep `skill/` and `prompts/` for the five overridden type names
      (`stale_artifact`, `motion_collision`, `range_exceeds_limit`, `contact_limited_stop`)
      to confirm no other doc still carries the old per-type instructions this change
      supersedes. (no matches in either directory)
