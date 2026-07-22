## 1. `verify_stage` helper

- [x] 1.1 Add `verify_stage(wp, label, bbox=None, vol_min=None, tolerance=0.1)` to
      `src/cq_verify.py`, following the `_fail("stage_mismatch", label, detail)` /
      return-input-unchanged shape of the existing three helpers. Raise (via `_fail`)
      when `bbox` is supplied and the actual bbox differs beyond `tolerance` on any
      axis, or when `vol_min` is supplied and the actual volume is below it. Raise a
      plain `ValueError` if neither `bbox` nor `vol_min` is supplied (caller error,
      not a geometry mismatch).
- [x] 1.2 Update the module docstring's list of three helpers to four.

## 2. Wrapper typed-error mapping

- [x] 2.1 Add a `"stage_mismatch"` entry to `_VERIFY_HINTS` in
      `src/run_cadquery_model.py` with a hint pointing at reworking the stage
      (`_translate_verify_marker` already keys off this dict, so no other wrapper
      change is needed).

## 3. Generated-script guidance

- [x] 3.1 In `prompts/part.md`, add the construction-plan requirement for the
      scratch-authoring path (no block, no archetype match): the script must open
      with named stages, each asserted via `verify_stage`, before adding the next
      stage's geometry. State that this does not apply to block- or
      archetype-based parts.
- [x] 3.2 Add `stage_mismatch` to the error-type table in `SKILL.md` (or the
      relevant per-phase file it now lives in), alongside
      `silent_boolean`/`feature_overflow`/`workplane_drift`.

## 4. Tests

- [x] 4.1 Add `test_cq_verify.py` (or extend the existing cq_verify test coverage if
      present) covering: bbox mismatch raises, volume-below-minimum raises, matching
      stage returns input unchanged, and the neither-bbox-nor-vol_min-supplied
      `ValueError`.
- [x] 4.2 Extend `tests/test_run_wrapper.py` with a `stage_mismatch` case mirroring
      the existing `silent_boolean` wrapper test (around line 295) -- a script that
      calls `verify_stage` with a failing expectation should yield a typed
      `stage_mismatch` error in the wrapper's JSON `errors` list.

## 5. Verification

- [x] 5.1 Run `uv run pytest tests/test_cq_verify.py tests/test_run_wrapper.py` (or
      the appropriate test file names) and confirm all new and existing tests pass.
- [x] 5.2 Update `IMPROVEMENT_PLAN.md` item 3 status from OPEN to DONE once the
      above lands.
