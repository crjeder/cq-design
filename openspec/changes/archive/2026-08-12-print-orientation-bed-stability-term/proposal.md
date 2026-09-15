## Why

`print_orientation.py` scores strength as orientation-neutral whenever a part has no
declared load or a declared `load_type=compression` (a resting weight doesn't stress the
interlayer bond, so no pose is penalized). In that case selection falls through entirely to
the severity-weighted support cost, with bed-contact area only breaking an exact tie. The
optimizer has no notion of whether a resting pose is physically stable: a candidate that
balances the part on a small facet, edge, or near-point contact — chasing a near-zero
support cost from a tiny feature — can beat the flat, obviously-correct face simply because
that flat face's small holes or bosses cost a few points of overhang. The result is a
recommended orientation that will tip over on the print bed. This has been observed on flat
compression parts (plates, plinths, bases) where the optimizer prefers a near-point balance
pose over the flat resting face.

## What Changes

- Add a **bed-stability score** computed per candidate: whether the posed mesh's
  center-of-mass, projected onto the bed plane (XY), falls within the convex hull of the
  candidate's bed-contact footprint. A candidate whose center of mass projects outside that
  hull will tip when set down and is unstable.
- Fold a minimum-footprint check into the same term: a bed-contact footprint below a small
  area/extent threshold is treated as unstable regardless of center-of-mass containment
  (a knife-edge or point contact is not a resting pose even if the math places the COM
  inside a degenerate hull).
- Make bed-stability a selection gate ahead of support cost in every optimization mode:
  unstable candidates are excluded from selection whenever at least one stable candidate
  exists, so support/strength/visual scoring only chooses among poses that will actually
  stay put on the bed. When every candidate is unstable (no flat resting face at all), the
  gate SHALL NOT eliminate every candidate — existing scoring proceeds unchanged as the
  fallback.
- Report the stability outcome (`stable: bool`, and the metrics behind it) per candidate in
  the tool's output so the rationale can explain when an unstable pose was excluded.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `print-orientation-optimization`: candidate scoring gains a bed-stability term, and
  selection in every mode gates out unstable candidates ahead of the existing
  strength/support/visual ordering.

## Impact

- `src/print_orientation.py`: new stability metric function, new field(s) on each scored
  candidate, `_select` gains a pre-filter step.
- `openspec/specs/print-orientation-optimization/spec.md`: requirement additions/edits for
  the new scoring term and the selection gate.
- `tests/` covering `print_orientation.py` (if present) need a case exercising the
  pathological near-point-balance scenario.
- No change to `quality_gate.py`'s consumption of `strength_score`/`support_score` — the new
  field is additive.
