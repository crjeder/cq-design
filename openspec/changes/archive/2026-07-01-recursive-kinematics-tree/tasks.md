## 1. Schema

- [x] 1.1 Add optional `children` (array, self-referencing the `kinematics` entry
      shape via a named `definitions` entry + `$ref`) to the `kinematics` entry in
      `src/build_plan_schema.json`, describing it as the joints mounted on this
      entry's `moving_union` (a top-level entry with no `children` reference is
      mounted on the static frame).

## 2. Plan validation

- [x] 2.1 In `src/plan_validate.py::_check_kinematics`, replace the flat
      `for entry in kinematics` loop with a recursive walk that visits every entry
      at every nesting depth (descend into `children`) and applies the existing
      per-entry checks (`moving_union` resolves, block/dof exist, joint contract)
      unchanged.
- [x] 2.2 Add/extend `tests/test_plan_validate.py` cases: a validation failure
      nested several levels deep under `children` is still reported with the
      correct `joint_id`; a valid multi-level chain passes.

## 3. Kinematic sweep

- [x] 3.1 In `src/kinematic_check.py`, add a helper that recursively collects an
      entry's swept subtree: itself plus every entry nested (at any depth) under
      its `children`. (Implemented as `units.iter_kinematics_entries`, shared with
      `plan_validate.py`'s flatten -- `iter_kinematics_entries([entry])` yields the
      entry's own subtree, so no separate helper was needed.)
- [x] 3.2 In `run_kinematic_check`, replace the flat entry loop with a recursive
      walk (mirroring `plan_validate.py`'s) so every entry at every depth is
      checked; replace the single moving mesh with the list of `(union_id, mesh)`
      pairs for the entry's subtree, and derive `fixed_ids` as
      `all_union_ids - subtree_ids` instead of `all_union_ids - {moving_id}`.
- [x] 3.3 Update `_sweep_collision` (or its call site) to apply the same per-step
      transform to every subtree mesh and report the first hit (step value plus
      colliding fixed union) across the subtree, preserving the existing
      `motion_collision` issue shape.
- [x] 3.4 Update the missing-STL guard to check every subtree union's STL exists,
      not just the single moving union's.

## 4. Tests

- [x] 4.1 Add a fixture plan in `tests/` with a two-joint chain (`forearm` nested
      under `shoulder`'s `children`) and assert the previously-spurious collision
      between the swept shoulder and the carried forearm no longer fires.
- [x] 4.2 Add a case where an unrelated/sibling union DOES collide with the swept
      subtree and assert `motion_collision` still fires and names that union.
- [x] 4.3 Add a regression case with no `children` fields (existing plans) and
      assert behavior is unchanged (fixed set = all other unions).

## 5. Docs

- [x] 5.1 Update the `kinematics` field description in `CLAUDE.md`'s
      `plan_validate.py` / `kinematic_check.py` table rows if their one-line
      summaries need to mention subtree-aware sweeping.
