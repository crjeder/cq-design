## Context

`cq_verify.py` already has four analogous construction-time bbox checks
(`verify_boolean`, `verify_feature_bounds`, `check_workplane`, `verify_stage`,
`verify_backed`). `blocks.joints.pin_hinge` already seats its knuckle join at the
tangent, not the center -- the C5 defect came from bypassing it, not from a missing
primitive. This is a small, localized addition to an existing module and existing
guidance documents; no new architecture or dependency.

## Goals / Non-Goals

**Goals:**
- Catch a flat body seated at a round feature's center (instead of its tangent) at
  construction time, via a bbox-only check consistent with the existing `verify_*`
  helpers.
- Route hinge authoring to the existing `pin_hinge` block first, so the check is a
  fallback guard rather than the primary defense.

**Non-Goals:**
- Detecting arbitrary center-vs-edge mistakes for every primitive shape (only the
  flat-support-vs-round-boss case that recurred in practice).
- A general `anchor()`/`place_at()` placement API (tracked separately in `TODO.md`
  under "BOSL2 attachables" -- much larger surface, not needed to close this gap).
- Any change to the plan schema, exporters, or CLI.

## Decisions

- **Bbox-only, like `verify_backed`, not a true tangency/contact check.** Matches
  the existing helpers' cost/precision trade-off (cheap, no mesh/BRep queries) and
  is sufficient: the failure mode is a support's bbox face landing at the boss's
  *center* coordinate, which a bbox comparison catches directly.
- **`overlap` default 1.0 mm, not 0.0.** `pin_hinge` itself deliberately straddles
  the tangent line by up to ~1 mm (`ov = min(leaf_w/2, d_outer/2, 1.0)`) because a
  bare tangent doesn't fuse in OCC. A zero-tolerance check would flag legitimate
  fusion margin; 1.0 mm accommodates it while still catching a full-radius bite.
- **New `boss_swallowed` error type, not reusing `unbacked_mate`.** `unbacked_mate`
  checks that a backer *reaches and contains* a feature's face -- the opposite
  failure shape (not enough support). This is a *support has too much of the boss*
  check; conflating the two would make the error message and the fix instructions
  wrong for one of the two cases.
- **Guidance change is routing-first, not check-first.** The contract-rule addition
  directs authors to `pin_hinge` before it mentions `verify_seated`, so the common
  case (a standard revolute knuckle hinge) never reaches hand-rolled geometry at
  all; `verify_seated` is scoped to the acknowledged-incompatible case.

## Risks / Trade-offs

- [Bbox-only check can miss a non-bbox-aligned tangent, e.g. a boss on a diagonal
  member] -> Mitigation: scenario coverage documents the axis-aligned case only,
  matching `verify_backed`'s existing scope; a diagonal case is out of scope for
  this change and not a regression (nothing catches it today either).
- [`overlap` default could mask a smaller but still-wrong seat] -> Mitigation: the
  default matches `pin_hinge`'s own known-good margin, so it's calibrated against a
  real, verified geometry rather than picked arbitrarily; callers needing a tighter
  budget can pass a smaller `overlap`.

## Migration Plan

Additive only: new function, new error type, new guidance lines. No existing
behavior changes, no rollback concerns beyond reverting the diff.
