## Why

Scratch-authored parts (no matching block, no matching archetype) currently get no
geometric feedback until the full script runs. A wrong topology introduced early in
the script surfaces several steps later as a cryptic OCC exception or a failed visual
review, instead of at the construction stage that actually caused it. This is item 3
of `IMPROVEMENT_PLAN.md`: a construction-plan / staged-assertion requirement so a
wrong stage fails immediately, by name.

## What Changes

- Add a `verify_stage(wp, label, bbox=None, vol_min=None)` helper to
  `src/cq_verify.py`: asserts a named construction stage's bounding box and/or
  minimum volume, raising a marked `RuntimeError`
  (`[cq-verify:stage_mismatch:<label>] ...`) on mismatch, returning `wp` unchanged
  otherwise so it chains inline like the existing `verify_boolean` /
  `verify_feature_bounds` / `check_workplane` helpers.
- Map the new marked error to a typed `stage_mismatch` entry in
  `run_cadquery_model.py`'s error handling, alongside the existing
  `silent_boolean`/`feature_overflow`/`workplane_drift` family.
- Require scratch-geometry scripts (the archetype/block fallback path) to open with
  an ordered construction plan -- named stages with expected bbox/volume -- asserted
  via `verify_stage` as the script executes. This requirement lives in
  `prompts/part.md` and does not apply when a block or archetype template already
  supplies verified topology.
- Document `stage_mismatch` in the SKILL.md error-type table.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `runtime-boolean-verification`: adds the `verify_stage` construction-stage
  assertion helper and its `stage_mismatch` typed error, and adds the scratch-part
  construction-plan requirement to the generated-script guidance.

## Impact

- `src/cq_verify.py`: new `verify_stage` function.
- `src/run_cadquery_model.py`: new `stage_mismatch` typed error mapping.
- `prompts/part.md`: construction-plan requirement for scratch (non-block,
  non-archetype) parts.
- `SKILL.md`: error-type table gains `stage_mismatch`.
- `tests/`: new/extended tests for `verify_stage` and the wrapper's typed-error
  mapping.
