## Context

`_check_joints` (src/plan.py) builds an undirected part graph from `joints`, BFS-walks it from `root_part` (`_bfs_mate_tree`), and treats any revisit as a "conflicting mate path". `mate_chain.compute_mate_poses` does the same BFS to derive poses and already skips parts that have a pose, so it needs no change for loops. Other consumers (`write_assembly`, `minimal_cutout_search`, `render_prompt`, the `quality_gate` routing check, `regen_prompt`) only read `compute_mate_poses` output or iterate `joints`; none assume acyclicity.

The HitsterTower ring (4 walls, dovetail corner joints) was forced onto per-part `placement` + `interfaces`, losing `joints[].params` as the single source for tooth depth, clearance, and pin/tail polarity.

Joint kinds in the inventory: `pin_hinge` has a `dof` (revolute); `dovetail_corner_joint` has none (rigid).

## Goals / Non-Goals

**Goals:**
- Allow cycles whose closure edges are all rigid joints.
- Turn the redundant edges into a consistency check with an actionable error.
- Keep pose derivation deterministic and unchanged.

**Non-Goals:**
- Closed kinematic chains (four-bar, folding loops): pose becomes a function of joint variables, needs a constraint solve, and breaks the `kinematics` subtree-sweep model.
- Loops inside `kinematics`.
- Load-sharing or tolerance-stack analysis of the loop.

## Decisions

**Rigid is "block has no `dof`".** The inventory already carries this; no new schema field. Alternative: a per-joint `rigid: true` flag. Rejected: it would let a plan mislabel a hinge and duplicates inventory truth.

**Spanning tree by BFS from `root_part`, in array order.** Same traversal as today, so existing plans derive identical poses. Alternative: least-squares fit over all edges. Rejected: it would make poses depend on tolerance error and silently average a bad dock instead of reporting it.

**Closure is a validation error, not a derivation input.** Residual = `inv(pose(Q) @ dock_B) @ (pose(P) @ dock_A)` per closure edge. This reuses `placement.to_matrix`. Tolerance 0.01 mm / 0.01 deg is a module constant, not config (YAGNI). Alternative: warn only. Rejected: an unclosed ring means the printed parts will not assemble, which is the defect the check exists to catch.

**Fix the parent-edge shortcut.** `_bfs_mate_tree` skips `nxt == parent[cur]` by node, so two joints between the same pair are silently accepted today. Track edges by index instead, so the second joint is classified as a closure edge (rigid: checked; kinematic: rejected).

**Where it lives.** `_bfs_mate_tree` returns `(parent, closure_edges)` where closure edges are `(joint_index)` entries; `_check_joints` classifies and evaluates them. The residual helper goes in `mate_chain.py` beside the derivation formula so the two stay in sync. It needs numpy, so import it lazily as `compute_mate_poses` does, keeping `test_plan.py` fast for plans without joints.

## Risks / Trade-offs

- [Clearance baked into dock] A block's clearance (0.1 mm in the tower) could be modeled in the dock rather than the geometry, making a correct ring fail closure. -> Spec says the check runs on docks; `dovetail_corner_joint` keeps clearance inside its geometry. Verify with the tower fixture in tests.
- [Float noise] Four composed rotations can drift. -> Tolerance 0.01 deg is well above double-precision error; use `numpy.allclose`-style per-component limits on the decomposed residual.
- [Order dependence] Which edge of a ring is the "closure" edge depends on `joints` order, so the error names a possibly arbitrary joint. -> Error text names every part on the closure edge and the residual; acceptable.
- [Weaker guarantee] A cycle with one rigid and one kinematic edge: closure edge may be the rigid one while the hinge is on the tree. -> Reject any cycle containing a `dof` edge, not just a `dof` closure edge. Implemented by checking all edges on the tree path between the closure edge's endpoints plus the closure edge itself.

## Migration Plan

Pure relaxation: every plan valid today stays valid and derives identical poses. The only newly rejected inputs are the previously-silent duplicate-pair joints with disagreeing docks. No schema version change. Rollback is reverting the commit.

## Open Questions

- Should HitsterTower be migrated to `joints` as part of this change or as a separate follow-up eval case? Default: add it as an eval case in a follow-up so this change stays validator-only.
