## 1. Helper module

- [x] 1.1 Create `src/cq_verify.py` with `verify_boolean(before, after, operation="cut", label="")` that raises `RuntimeError` (carrying a helper-owned marker + the `label`/`operation`) only when volume, face count, and centroid are all unchanged within tolerance; returns `after` otherwise.
- [x] 1.2 Add `verify_feature_bounds(before, after, label="", tolerance=0.1)` raising `RuntimeError` (same marker) with per-axis overflow when post-feature geometry extends past the base bounding box; returns `after` otherwise.
- [x] 1.3 Add `check_workplane(wp, label="", expected_origin=None, tolerance=0.1)` raising `RuntimeError` (same marker) with expected/actual origin + drift distance when `wp.plane.origin` drifts past tolerance; returns `wp` otherwise; no unconditional print.
- [x] 1.4 Keep imports to CadQuery + stdlib only; no `blocks/__init__` re-export, no `inventory.json` entry.

## 2. Wrapper error mapping

- [x] 2.1 In `src/run_cadquery_model.py`, detect the verify-helper marker on a `RuntimeError` from the model subprocess and emit `type: "silent_boolean"`, `type: "feature_overflow"`, or `type: "workplane_drift"` (with `label`, `message`, `hint`) before the generic `occ_exception` fallback.
- [x] 2.2 Ensure a `RuntimeError` without the marker still falls through to existing generic handling (no misclassification).
- [x] 2.3 Keep the JSON contract keys unchanged; the new types are values of the existing `errors[].type` field.

## 3. Prompt & reference guidance

- [x] 3.1 Add a generated-script rule (`SKILL.md` "Generated script rules") and `prompts/part.md` guidance on when to wrap a boolean in a verify call (computed-offset tool, off-center feature, emboss/deboss merge), when to assert a workplane origin (after `.center()`/`.hole()` before placing a feature on a reused workplane), and when not to (trivially overlapping primitives).
- [x] 3.2 Add `silent_boolean`, `feature_overflow`, and `workplane_drift` rows to the `SKILL.md` "Error handling reference" table.
- [x] 3.3 Cross-reference the now-executable checks from `reference/CadQuery Anti-Patterns.md` / `reference/emboss_text.md` where the silent-boolean and `.center()` origin-shift traps are described in prose.

## 4. Tests

- [x] 4.1 Add `tests/test_cq_verify.py`: true no-op cut raises; effective cut passes; equal-volume relocation (centroid shift) passes; feature within bounds passes; overflow raises with per-axis magnitude; drifted workplane origin raises; on-anchor workplane passes.
- [x] 4.2 Add a wrapper-level test that a script raising the verify marker yields `errors` with `type: "silent_boolean"` / `feature_overflow` / `workplane_drift` and the `label`, and that an unrelated `RuntimeError` does not.
- [x] 4.3 Run `uv run pytest tests/test_cq_verify.py tests/test_run_wrapper.py` and confirm green.

## 5. Docs & bookkeeping

- [x] 5.1 Add the `src/cq_verify.py` row to the CLAUDE.md core-scripts table.
- [x] 5.2 Tick the `cq_debug_helpers.py` item in `TODO.md` (line under "Independent changes") noting it shipped via this change.
