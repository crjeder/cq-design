## 1. Extract the shared interference primitive

- [x] 1.1 Create `src/interference.py` with `colliding_names(moving_mesh, manager, penetration_tol_mm: float | None) -> set[str]`: return collided names on any `hit` when `penetration_tol_mm is None`, else only when the deepest contact `depth` exceeds it (D1, D2).
- [x] 1.2 Add `check_interference(subject_mesh, others, *, exclude=frozenset(), penetration_tol_mm=None) -> set[str]` that builds a `CollisionManager` over `others` minus `exclude` and calls `colliding_names` once (D3).
- [x] 1.3 Add the centralized backend probe (trimesh + `CollisionManager` import) the callers use to decide whether to degrade; the primitive signals unavailability, callers own the `check_skipped` issue wording (D4).
- [x] 1.4 Keep the module trimesh + python-fcl only (no CadQuery import), matching `keep_out_check`/`kinematic_check`.

## 2. Refactor keep-out validation onto the primitive

- [x] 2.1 Replace the inline `CollisionManager` build + `in_collision_single` call in `keep_out_check.run_keep_out_check` with `check_interference(zone_mesh, foreign_unions, exclude=declaring_part_unions, penetration_tol_mm=None)` (preserve the any-contact semantics via `None`).
- [x] 2.2 Route the missing-backend path through the primitive's probe while keeping the existing `check_skipped` message/hint and the existing missing-STL `check_skipped` branch unchanged.
- [x] 2.3 Preserve the exact `keep_out_violation` message/hint/extra keys (`zone_part`, `zone_name`, `offending_union`) and the sorted-names emission order.

## 3. Refactor the kinematic per-pose collision onto the primitive

- [x] 3.1 Replace the `manager.in_collision_single(...)` + depth-threshold logic inside `kinematic_check._sweep_collision` with `colliding_names(moved, manager, penetration_tol_mm)`, keeping the prebuilt pose-reused manager and the `penetration_tol_mm` default (0.1).
- [x] 3.2 Leave the range-vs-`mechanical_limit` scalar check, `iter_poses`/sweep, and swept-subtree rigid carry entirely in `kinematic_check` (Non-Goal: no DoF absorption).

## 4. Tests

- [x] 4.1 New `tests/test_interference.py`: unit-test `colliding_names`/`check_interference` for overlap, no-overlap, exclusion-set, the touch-vs-depth boundary (`None` counts a bare contact, a small float does not), and backend-absent degrade signalling.
- [x] 4.2 Confirm every existing `keep_out` scenario test passes unchanged (behavior-preservation guard).
- [x] 4.3 Confirm every existing `kinematic` scenario test (range check + collision sweep + degrade) passes unchanged.

## 5. Documentation and extension seam

- [x] 5.1 Update `CLAUDE.md` Core Scripts table: add `src/interference.py` and note `keep_out_check`/`kinematic_check` now consume it.
- [x] 5.2 Add a short module docstring / comment in `interference.py` documenting the assembly-clearance placeholder as the next intended caller (static single-subject via `check_interference` with its own `type`/`hint`), per D5.
- [x] 5.3 `openspec validate generalize-interference-assertion --strict`.
