## Why

`print_orientation.py` spends about 107 s of a 129 s build in the candidate loop (205 candidates, ~0.5 s each). Topology caches and normal merging are already done, so the remaining cost is per pose: `mesh_io._is_bridge` takes 52 s (about 754 regions per candidate, only ~10% pass the 80 degree gate yet all are visited, and each survivor pays a qhull `ConvexHull` with a `mkstemp` plus two `np.unique`, one with `axis=0`), and per-pose triangle centroids are recomputed 3x per candidate (~20 s, plus 6.5 s of `triangles` gather and 17 s behind `bed_contact_mask`).

## What Changes

- Compute base-mesh triangle centroids once in `optimize_orientation`; derive each pose's centroid z as `centroids @ R[2] + tz` and share it between `bed_contact_mask` and `_is_bridge`.
- Build the face-adjacency edge keys and pairs once per base mesh and reuse them for every pose (adjacency is rotation-invariant).
- In `_is_bridge`, apply the 80 degree average-angle gate to all regions at once (`bincount` over component labels) and loop only over survivors.
- Replace `np.unique(edges, axis=0)` with 1-D edge keys, and replace the qhull oriented-bounds call for tiny regions with a closed-form or numpy rectangle.
- No change to which orientation is chosen, to scores, or to any region's bridge decision.

## Capabilities

### New Capabilities

### Modified Capabilities
- `overhang-analysis`: bridge detection gates regions in bulk and does not run per-region hull or 2-D `np.unique` work for regions that fail the gate.
- `print-orientation-optimization`: pose-invariant geometry (centroids, adjacency keys) is computed once per mesh, not per candidate.

## Impact

- `src/mesh_io.py` (`bed_contact_mask`, `_is_bridge`, `overhang_regions`), `src/print_orientation.py` (`optimize_orientation`, `_bed_contact_mask`, metric helpers).
- Internal signatures only (optional precomputed arguments); `support_cost`, `overhang_metrics` and the quality-gate JSON contract are unchanged.
- No new dependencies. Candidate pruning by a support-cost lower bound is excluded unless a post-change profile shows support cost still dominates.
