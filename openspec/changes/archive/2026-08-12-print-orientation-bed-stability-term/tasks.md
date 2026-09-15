## 1. Stability metric

- [x] 1.1 Add a `_stability_metrics(posed, contact_mask)` helper to `src/print_orientation.py`
      that returns `stable: bool` given the posed mesh and the bed-contact face mask already
      computed by `_support_metrics`: collect the contact faces' XY vertices, treat fewer
      than 3 distinct points as unstable, otherwise build the 2D convex hull and test whether
      `posed.center_mass[:2]` falls inside it.
- [x] 1.2 Wire the helper into `optimize_orientation`'s per-candidate loop so each candidate
      dict gains a `stable` key alongside `strength`/`support`/`bed_contact`/`visual`.

## 2. Selection gate

- [x] 2.1 In `_select`, restrict `candidates` to the stable subset before applying each
      mode's existing key, falling back to the full set when no candidate is stable.
- [x] 2.2 Update `_rationale` to note when the stability gate excluded one or more
      candidates.
- [x] 2.3 Add `stable` to the dict returned by `optimize_orientation`.

## 3. Tests

- [x] 3.1 Add a case to `tests/test_print_orientation.py` covering a mesh with a small
      corner/edge feature that would win on support cost alone but is unstable (fewer than 3
      contact points or COM outside the footprint hull), asserting the flat stable face is
      selected instead.
- [x] 3.2 Add a case asserting `stable: True` is reported for a normal flat-bottomed part and
      the rationale mentions exclusion only when it actually occurred.
- [x] 3.3 Add a case (or reuse an existing degenerate mesh, e.g. a sphere-like mesh with no
      flat resting face) asserting the all-unstable fallback still returns a recommendation.

## 4. Spec sync

- [ ] 4.1 Run the project's spec archive/sync step to merge the delta spec in
      `specs/print-orientation-optimization/spec.md` into
      `openspec/specs/print-orientation-optimization/spec.md` once implementation lands.
