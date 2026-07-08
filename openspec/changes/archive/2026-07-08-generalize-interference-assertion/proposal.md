## Why

Two whole-model gate stages already answer the same underlying question -- "do these
two posed bodies overlap?" -- with two independent copies of the trimesh + python-fcl
machinery: `keep_out_check.py` (a declared zone vs every foreign union) and the
per-pose collision inside `kinematic_check.py` (a swept union vs every union outside
its subtree). cad-khana's `assert_no_interference` is the same primitive named once
and reused. Extracting one shared interference core removes the duplication, makes the
overlap test independently testable, and turns "does A overlap B, excluding a self-set"
into a one-call capability that future interference checks (assembly-clearance volumes,
feature no-overlap assertions) can reuse instead of re-deriving.

## What Changes

- Introduce a shared static interference primitive: given two assembled/posed meshes
  and an **exclusion set**, report whether they overlap, emitting the existing
  `{source, severity, type, message, hint}` gate contract on a violation and degrading
  to a single `check_skipped` warning when the collision backend is unavailable. Same
  tooling (trimesh + python-fcl) the two stages use today.
- Refactor `keep_out_check.py` to be the primitive's first consumer: a keep-out zone is
  the `subject`, every foreign union is an `other`, and the exclusion set is the zone's
  own declaring part's real unions. **Behavior-preserving** -- the existing
  `keep_out_violation` output and degrade behavior are unchanged.
- Refactor the per-pose collision test in `kinematic_check.py` to call the same core.
  Its DoF semantics are **not** absorbed: the `required_range`-vs-`mechanical_limit`
  scalar bound check and the sweep / trajectory / swept-subtree rigid-carry stay in the
  kinematic stage. The stage becomes a *consumer* of the interference primitive, not an
  instance of the keep-out concept. **Behavior-preserving.**
- Leave a documented extension point (not shipped here) showing how a future
  assembly-clearance placeholder volume plugs into the same primitive as a second kind
  of declared subject.

## Capabilities

### New Capabilities
- `interference-primitive`: the model's single notion of geometric interference between
  two posed bodies -- an overlap test with a caller-supplied exclusion set, the shared
  structured-issue contract on violation, and graceful degradation to `check_skipped`
  when the collision backend is missing. Consumed by keep-out validation and the
  kinematic per-pose collision test.

### Modified Capabilities
<!-- None. keep-out-validation and kinematic-range-validation refactor onto the shared
     primitive without changing any required behavior (verified by their existing
     scenario tests); this is an internal consolidation, not a spec-level change. -->

## Impact

- New `src/interference.py` (or equivalent shared module): the `interfere` /
  `check_interference` core (trimesh + python-fcl), extracted from the two stages.
- `src/keep_out_check.py`: refactored to call the shared core; output unchanged.
- `src/kinematic_check.py`: per-pose collision refactored to call the shared core;
  range check and sweep untouched.
- Tests: new unit tests for the primitive in isolation (overlap, no-overlap,
  exclusion-set, backend-absent degrade); existing `keep_out` and `kinematic` scenario
  tests must continue to pass unchanged as the behavior-preservation guard.
- Out of scope (separate follow-ups): assembly-clearance placeholder authoring path;
  feature presence/placement assertions (`plan-feature-assertions`, which begins with an
  `interfaces[]` schema tightening); `assert_clearance` (a proximity/gap check, not
  overlap -- the inverse of this primitive, already partly served by
  `plate_clearance_check`).
