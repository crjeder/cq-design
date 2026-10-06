## Context

`_sampled_thickness` loops over sampled faces; per ray it selects triangles by two half-space tests, then runs vectorized Moeller-Trumbore over the survivors. Work is O(samples x triangles) with a Python-level iteration per ray. TODO item 1 asks for batched `trimesh.ray` (embree/rtree) or chunked rays plus a bbox prefilter. Only rtree is a declared dependency; embreex is optional.

## Goals / Non-Goals

**Goals:**
- Same per-face thickness as today (within float tolerance), much lower wall time on 3000-sample runs.
- No new dependency.

**Non-Goals:**
- Profiling other hot paths (TODO items 2-9).
- Changing sampling, thresholds, grouping, or classification in `_thin_regions`.
- Requiring embree.

## Decisions

- **Use `mesh.ray.intersects_location(origins, dirs, multiple_hits=True)`** over a single query. trimesh picks the fastest backend present; the rtree path queries triangle bboxes against each ray segment, which is the bbox prefilter the TODO asks for. Alternative (chunked numpy over all triangles) keeps O(S x T) cost; rejected.
- **Filter hits in numpy:** keep hits with `face_normals[index_tri] . dir[index_ray] > 1e-9` and `t = |loc - origin| > tmin`, then `np.minimum.at` per ray. This reproduces the current exit-wall rule exactly, so results match the reference path.
- **Origin offset:** origins sit on the surface (face centers), so the entry triangle is hit at t~0 and is dropped by `tmin`/facing; no origin nudge needed.
- **Keep `prefilter=False`** as the brute-force reference; `prefilter=True` (default) becomes the batched path. The existing equivalence test continues to guard it. The old half-space prefilter loop is removed.

## Risks / Trade-offs

- Diagonal rays make large bboxes in the rtree path, so worst case degrades toward today's cost, not below it meaningfully. Acceptable; CAD walls are mostly axis-aligned.
- Hits on shared edges/vertices may return duplicates; harmless under min-reduction.
- trimesh backend differences (embree float32) can shift t by ~1e-6; the test uses allclose.
