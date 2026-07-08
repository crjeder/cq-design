## Why

A CadQuery `.cut()` / `.union()` / `.intersect()` that fails to overlap its tool
produces **no change and no exception** -- the script runs green, and the missing
feature only surfaces downstream (or not at all) as a vague `non_watertight` /
`dimension_mismatch` finding that never names the boolean that silently no-op'd.
The project already documents this trap as prose in `reference/emboss_text.md` and
`reference/CadQuery Anti-Patterns.md`, but nothing in the part loop actually executes
a check, so the correction prompt can't tell Claude *which* feature vanished. This
change anchors that check as a runtime assertion the generated script performs at
construction time, adapting the approach from
`thereprocase/cad-skill/scripts/cq_debug_helpers.py` (reimplemented, not vendored --
the project is PolyForm Noncommercial and upstream declares no license).

## What Changes

- Add a small, dependency-free helper module under `src/` (import-visible to generated
  scripts via the existing `PYTHONPATH=<src>`) exposing at minimum `verify_boolean(before,
  after, operation, label)` -- raises when volume, face count, and centroid are all
  unchanged after a boolean -- `verify_feature_bounds(before, after, label, tolerance)`
  -- raises when new geometry extends past the base body's bounding box -- and
  `check_workplane(wp, label, expected_origin, tolerance)` -- raises when a workplane's
  origin has drifted from the expected point (the `.center()` / `.hole()` origin-shift
  trap), so a feature is not silently placed at the wrong location.
- Teach the part-generation prompt (`prompts/part.md`) and the generated-script rules
  (`SKILL.md`) when to wrap a boolean in a verify call (a computed-offset tool, an
  off-center feature, an embossed/debossed text merge) and when to assert a workplane
  origin (after a `.center()`/`.hole()`, before placing a new feature on a reused
  workplane).
- Map the helpers' `RuntimeError` in `run_cadquery_model.py` to new structured error
  types (`silent_boolean`, `feature_overflow`, `workplane_drift`) carrying the offending
  `label`, so the bounded fix loop gets a targeted correction naming the exact feature
  or workplane instead of a generic geometry failure.
- Extend the error-handling reference table in `SKILL.md` with the three new types.

## Capabilities

### New Capabilities
- `runtime-boolean-verification`: an in-script assertion helper that catches silent
  boolean failures, feature-bounds overflow, and workplane-origin drift at construction
  time, plus the generated-script convention for when to call it.

### Modified Capabilities
- `structured-errors`: the wrapper gains three new typed error categories
  (`silent_boolean`, `feature_overflow`, `workplane_drift`) translated from the helper's
  `RuntimeError`, with hints and the feature/workplane `label` in the error object.

## Impact

- New file: `src/cq_verify.py` (helper module) + its tests.
- Modified: `src/run_cadquery_model.py` (RuntimeError -> typed-error mapping),
  `prompts/part.md` and `SKILL.md` (when-to-use guidance + error table row),
  `reference/CadQuery Anti-Patterns.md` (cross-reference the now-executable check).
- No new third-party dependency (helpers use only CadQuery, already required).
- Adaptation is clean-room from the documented behavior, not a copy of upstream source.
