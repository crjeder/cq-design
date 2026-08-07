## Context

`kinematic_check.py` sweeps a moving union through a declared range and asks, at each
pose, "does this interfere?" Two layers of that are wrong, and the C5 Phone-Holder is the
worked example for both (see `proposal.md` for the measurements).

The measurement layer: `interference.colliding_names` thresholds fcl's per-contact
`depth`. On the phone-holder fold that value reads 7.2 mm where the true overlap is
0.09 mm³, and is non-monotonic in the real overlap (39.9 mm at -80 deg / 1337 mm³ vs
30.0 mm at -90 deg / 5557 mm³). Mesh-mesh contact depth is computed per intersecting
triangle pair and is ill-conditioned for the large near-coplanar triangles flat printed
faces tessellate into.

The semantic layer: the sweep is a pass/fail over a fixed range. A joint whose closed
position is a contact stop -- which describes most folding designs -- can never pass,
because the poses past the stop necessarily interpenetrate even though the mechanism
cannot reach them. The shipped phone-holder cradle folds cleanly and its printed part
works; a plan declaring the natural `required_range: [-90, 0]` would get a 5.5 cm³
collision error.

Two prerequisites already shipped and this design composes with them: `blockless-kinematics`
(entries may omit `block`, sourcing `mechanical_limit` from the entry, emitting
`range_check_not_applicable`) and `build-artifact-freshness` (stale unions are excluded
from the sweep with a `stale_artifact` error).

## Goals / Non-Goals

**Goals:**

- Measure interference by a quantity that means what it says, so designed flush contact is
  never reported as binding.
- Let a joint whose travel ends at a mechanical stop report *where it stops* rather than
  fail.
- Make a cut-short sweep say how far the joint got, at a resolution better than `step`.
- Leave keep-out semantics and every existing block-backed plan behaving exactly as today.

**Non-Goals:**

- Minimum-cutout search ("how tall must the notch be for this to clear?"). That is a search
  loop over geometry edits, not a measurement change; it stays open in `TODO.md`.
- A declared separating/stop plane. Considered and deferred -- see Decisions.
- Any change to `plate_clearance_check.py`, which measures minimum surface distance and
  does not route through `interference.py`.
- Dynamics of any kind: this stays a static per-pose interference test.

## Decisions

### Boolean intersection volume as the interference measure, via manifold3d

Replace depth thresholding with the volume of the boolean intersection, computed with
`manifold3d` through `trimesh.boolean.intersection(..., engine="manifold")`. fcl is kept
as the broadphase: it is fast and its *contact/no-contact* answer is reliable -- only its
`depth` is not. The boolean runs only on a broadphase hit, so clear poses cost exactly
what they cost today.

*Why volume:* it is the physically meaningful quantity, it is monotonic in how badly two
bodies interfere, and it is what the phone-holder session's hand-written sweeps used
across seven rounds and got right ("Z=15 still binds by 0.14 mm³").

*Alternatives considered.* Signed-distance sampling of contact-region vertices
(`trimesh.proximity`) needs no new dependency but is approximate -- a pure edge-edge
crossing with no vertex inside the other body reads as zero. Eroding the moving mesh by
the tolerance and testing plain contact avoids depth entirely but inward vertex offset is
unreliable on coarse tessellation. Both trade correctness for dependency count; the
dependency is cheap and the correctness is the whole point of the change.

### No fallback when the boolean engine is missing

If `manifold3d` is unavailable the stage emits `check_skipped`, exactly as it already does
when fcl is missing. There is deliberately no second measure.

Two measures with different sensitivity would make findings incomparable between machines
and runs, and the obvious fallback is the depth thresholding this change exists to remove
-- a "graceful degradation" straight back into the bug. A skipped check is honest; a
quietly weaker check is not. This is also the user's explicit instruction for this change.

### `stop_on_contact` as an opt-in plan field, defaulting to false

A contact-limited joint is a property of the design, not something to infer. Inferring it
("if it collides near the end of range, probably a stop") would silently swallow real
binding. Making it opt-in keeps every existing plan on today's semantics and forces the
author to state the intent.

*Alternatives considered.* Making contact-limited the default and requiring opt-out was
rejected: it changes the meaning of every existing plan. A separate `stop_range` field
duplicating `required_range` was rejected as redundant -- the required range already
expresses the ideal travel, and the finding reports the shortfall against it.

### Bisection to refine the stop value

On a cut-short sweep, bisect between the last clear value and the first binding value for
a fixed 8 iterations, giving `step/256` resolution. Fixed count over a tolerance loop:
predictable cost, no configuration, and 8 is already well past the precision the mesh
tessellation itself supports. This is the manual binary search the phone-holder session
ran by hand, made part of the tool.

### Volume tolerance default of 0.1 mm³, and it stays a knob

`--penetration-tol` changes meaning from mm to mm³. On the phone-holder geometry a
0.1 mm³ budget puts the detected stop within about half a degree of true tangency (true
contact -53.5 deg; 0.093 mm³ at -54 deg), and measured zero at the last clear pose, so
tessellation noise does not manufacture volume at flush contact there. That is one
model's calibration, not a law -- curved mating surfaces with coarser chord error will
overlap more at nominal tangency, so the flag stays exposed and documented rather than
being hard-coded.

Renaming the flag (rather than reusing `--penetration-tol` with new units) is worth the
churn: the old and new defaults are both `0.1`, so a silent unit change would be invisible
in scripts and logs.

### Deferred: the declared separating / stop plane

The explore session raised letting the author declare a plane that separates free space
from populated space -- the plate's front face here. Recording why it is not the mechanism:
on this very model it fails as a global certificate, because the cradle's hinge knuckle
legitimately lives *behind* the plate's front-face plane, between the ears and through the
notch. Its real insight is that the plate face is the **stop surface**, and
`stop_on_contact` captures that directly from geometry with nothing for the author to
declare or get wrong. A declared plane may still earn a place later as a fast path or as a
way to name the expected stop; it should not be the correctness mechanism.

## Risks / Trade-offs

- **Boolean cost on heavily-interfering sweeps** → The boolean runs only on broadphase
  hits, and both modes stop at the first binding pose (contact-limited stops by
  definition; hard-range returns on first collision). Worst case is one boolean per
  colliding pose up to the first bind, plus 8 for bisection.
- **New runtime dependency** → `manifold3d` is a small self-contained wheel, verified
  importable and correct against the phone-holder STLs during exploration. Mitigated by
  the `check_skipped` path if it is ever absent.
- **`stop_on_contact` used to paper over real binding** → The stage still reports the stop
  and the shortfall as a warning naming the colliding union, so the information is not
  hidden; only its severity changes. The risk is a designer ignoring a warning, which is a
  judgement they are entitled to make.
- **Tolerance is a heuristic calibrated on one model** → Exposed as a flag, documented in
  the design and CLI help, with the phone-holder calibration recorded here so a future
  adjustment starts from evidence rather than taste.
- **Findings change for existing models** → Intended: a pose previously reported as binding
  on an ill-conditioned depth value, whose true volume is within tolerance, stops being
  reported. Spec'd explicitly as the defect being fixed, not a regression.

## Migration Plan

No data migration; `BUILD_PLAN.json` gains an optional field with a backwards-compatible
default. Order: primitive first (behaviour-preserving for keep-out), then the sweep
reporting, then `stop_on_contact`.

Rollback is per-commit; the plan field is inert if the code is reverted, since
`additionalProperties: false` would then reject it -- so a rollback must revert the schema
together with the code, or leave the schema permissive. Simplest: revert both.

## Open Questions

- Should the contact-limited shortfall warning be suppressed entirely when the achieved
  range covers some author-declared "acceptable" fraction? Deferred -- no evidence yet that
  the warning is noisy, and a threshold invented now would be arbitrary.
- Should `plate_clearance_check.py` eventually route through the primitive for consistency?
  Out of scope here; it answers a different question (minimum gap, not overlap).
