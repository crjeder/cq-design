## Why

The C5 Phone-Holder session hand-rolled a hinge knuckle instead of routing to the
existing `blocks.joints.pin_hinge`, and seated the riser box's Z-top and Y-face at
the knuckle disc's *center* (`PIVOT_Z`, `PIVOT_Y`) instead of its tangent
(`PIVOT_Z - KNUCKLE_R`, centered on `PIVOT_Y`). The union stayed watertight (volume,
face count, bbox all plausible), so it survived nine correction rounds undetected --
only a rendered preview showed the knuckle as a disc half-buried in a box instead of
a free-standing ear (see `TODO.md`, "C5 hinge ear center-vs-edge"). Neither
`script_lint`'s AST pass nor any `cq_verify` guard can see this: the riser's Z-band
and the circle's center are set from unrelated arithmetic (`BAR_H + EAR_STANDOFF`
vs. two script-local literals), not a shared name a lint pass could trace.

## What Changes

- Add `cq_verify.verify_seated(support, boss, axis, label, overlap=1.0)`: a
  construction-time bbox check that raises when a flat `support` body bites more
  than `overlap` mm past the tangent plane of a round `boss` body along `axis`,
  catching a center-seated riser/knuckle join at build time instead of only in a
  rendered preview.
- Add a routing note to `prompts/part.md` / `skill/phase3_build.md`: a print-in-place
  revolute knuckle hinge SHALL be built via `blocks.joints.pin_hinge` (which already
  seats its leaves at the knuckle tangent) rather than hand-rolled from primitives,
  unless the part's geometry is incompatible with `pin_hinge`'s two-leaf shape --
  in which case the hand-rolled knuckle SHALL be guarded with `verify_seated`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `runtime-boolean-verification`: add the `verify_seated` construction-time check
  to `src/cq_verify.py`.
- `part-authoring-guidance`: add the pin-hinge routing rule (and the
  `verify_seated` fallback guard) to the enumerated contract-rule set.

## Impact

- `src/cq_verify.py`: new `verify_seated` function, reusing `_AXIS_TOKENS`, `_fail`,
  `_solid` already defined there.
- `tests/test_cq_verify.py` (or wherever `cq_verify` is tested): new cases for
  `verify_seated`.
- `prompts/part.md`, `skill/phase3_build.md`: one new enumerated contract-rule line
  each.
- No schema, CLI, or export-format changes.
