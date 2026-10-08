## Context

`optimize_orientation` copies the base mesh per candidate and applies a rotation. Per pose it then calls `bed_contact_mask`, `support_cost` -> `overhang_regions` -> `_is_bridge`, `_gentle_incline_fraction` and `_stability_metrics`. Profile of a 205-candidate run: `_is_bridge` 52 s, centroid recomputation (`triangles_center`, `triangles.mean`) ~20 s, `triangles` gather 6.5 s, `bed_contact_mask` 17 s, `_overhang_angles` 4.6 s, `_build_height` 5.8 s. Face adjacency, edge keys and face areas are rotation-invariant; centroid z and face normals are the only pose-dependent inputs.

## Goals / Non-Goals

**Goals:**
- Cut per-candidate cost by removing pose-invariant recomputation and avoiding work for regions that cannot be bridges.
- Identical scores, chosen orientation, and bridge flags.

**Non-Goals:**
- Candidate pruning via a support-cost lower bound (only if the post-change profile shows support cost dominating and `_select` is monotone in it).
- Changes to `_overhang_angles` or `_build_height` beyond what falls out of the shared arrays.

## Decisions

1. **Centroids once, z per pose.** `centroids @ R[2] + tz` equals the posed centroid z up to float rounding; `bed_contact_mask` and `_is_bridge` take an optional `centroids_z`. Alternative (cache on the posed trimesh) rejected: the cache is rebuilt after `apply_transform`, which is the cost being removed. Rounding at the `FIRST_LAYER_BAND_MM` and `1e-6` thresholds is covered by a parity test over the candidate set.
2. **Adjacency keys/pairs once per base mesh.** Passed into `overhang_regions` via the existing `ctx` dict, pre-seeded by `optimize_orientation`. Posed meshes share face/vertex indexing with the base, so keys stay valid.
3. **Bulk gate before the loop.** Compute the area-weighted mean angle per region with `np.bincount` over component labels and call `_is_bridge` only for regions at or above `BRIDGE_MIN_DEG`; the in-function gate stays so direct callers are unaffected.
4. **1-D edge keys for boundary detection.** `lo * nverts + hi` with `np.unique(return_counts=True)` replaces `np.unique(axis=0)`.
5. **Cheap rectangle for tiny regions.** Regions with few unique vertices get an exact closed-form rectangle only where it provably equals the `oriented_bounds_2D` min-area result; otherwise fall back to qhull. Histogram region face counts first and skip this step if few regions are tiny.

## Risks / Trade-offs

- [Float drift flips a near-threshold face] -> parity test comparing per-candidate scores and bridge flags, old vs new, on fixture meshes with many small overhang regions.
- [Closed-form rectangle diverges from the qhull result] -> restrict to exact cases, cover with the parity test, fall back otherwise.
- [Gain smaller than estimated] -> profile one candidate before steps 3 and 5 as the TODO says; drop steps that do not move the profile.
