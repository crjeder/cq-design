## Why

`joints` requires a single-rooted tree, so a ring of rigidly mated parts (the HitsterTower: four walls joined by dovetail corner joints, wall_a->wall_c->wall_b->wall_d->wall_a) cannot be expressed. The workaround (explicit per-part `placement` + `interfaces`) loses the one-source-of-truth for the joint's parameters and hides the walls from the joint-linked routing check. For rigid joints a loop is not a kinematic problem, only a consistency constraint, so the tree restriction is stricter than it needs to be.

## What Changes

- `plan.py validate` accepts cycles in the mate graph when every edge on the cycle is a **rigid** joint (its block's inventory descriptor has no `dof`). Poses are still derived along a BFS spanning tree from `root_part`.
- Each non-tree edge becomes a **loop-closure check**: the pose implied by that edge must equal the already-derived pose within tolerance (0.01 mm, 0.01 deg). A residual beyond tolerance is a blocking error naming the joint, the parts, and the residual.
- A cycle containing any joint whose block has a `dof` (e.g. `pin_hinge`) stays rejected as a conflicting mate path: closed kinematic chains remain out of scope.
- Two joints between the same pair of parts are currently skipped silently by the BFS parent-edge shortcut; they are checked as closure edges too.
- `kinematics` stays tree-only. Unchanged.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `joint-mate-entity`: the "mate graph is a single tree" requirement relaxes to "spanning tree plus closure-checked rigid loops"; adds the closure-residual requirement.

## Impact

- `src/plan.py`: `_bfs_mate_tree`, `_check_joints` (cycle classification, closure check).
- `src/mate_chain.py`: expose edge residual helper (reuses `to_matrix`); `compute_mate_poses` unchanged (already skips posed parts).
- `src/build_plan_schema.json`: description text of `root_part`/`joints` only; no structural change.
- `tests/test_plan.py`: replace the cycle-rejected test with rigid-loop accepted / hinge-loop rejected / open-loop rejected tests.
- `prompts/planning.md`, `skill/phase2_planning.md`: drop "single tree" wording if present.
- No change to `write_assembly.py`, `quality_gate.py`, `render_prompt.py`.
