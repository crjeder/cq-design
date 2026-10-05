## Context

`_thin_regions` samples up to `max_samples` faces (default 2000) and calls `_ray_thickness` once per sample against all triangles. The inward ray from a face of a closed mesh exits through the opposite wall, whose outward normal points along the ray: `n_tri . d > 0`. The `det` sign in Moeller-Trumbore encodes the same test but is computed only after the cross products, so it saves nothing today.

## Goals / Non-Goals

**Goals:**
- Cut per-ray cost by filtering triangles with one cheap half-space test before Moeller-Trumbore.
- Identical thickness output on watertight meshes.

**Non-Goals:**
- Spatial acceleration structures (BVH/rtree), new dependencies, changing the sample cap or the region grouping.
- Handling open or non-manifold meshes differently (`mesh_io` already enforces watertightness upstream).

## Decisions

- **Facing test as a separating plane through the ray origin in normal space.** Keep triangles with `n_tri . d > eps` (small eps so grazing triangles are not dropped by float error; the existing `abs(det) > 1e-9` already rejects parallel ones).
- **Second half-space: in front of origin.** Drop triangles whose three vertices all satisfy `(v - o) . d <= tmin`. Cheap (matvec on vertices) and removes the half behind the origin.
- **Batch the facing test, not the intersection.** Compute `N @ D.T` once for all sampled rays (bounded: 2000 x n_faces booleans; chunk rays if memory matters). Intersection stays per-ray on the subset, so peak memory stays small and `_ray_thickness` keeps its signature apart from taking the subset arrays.
- Alternative rejected: fully vectorizing Moeller-Trumbore across rays x triangles, which is O(rays x faces) memory and gains little over the filter.

## Risks / Trade-offs

- [Non-watertight or flipped-normal mesh makes the facing assumption wrong] -> thickness path is only reached for meshes that passed the watertight check; equivalence test covers a flipped-normal-free fixture, and eps is kept conservative.
- [Float error at grazing angles drops a true hit] -> eps on the facing test; equivalence test asserts exact match with the unfiltered cast on the existing thin-interface fixtures.
- [Speedup smaller than expected on small meshes] -> acceptable; benchmark in tasks, keep the change only if it is faster on a dense fixture.
