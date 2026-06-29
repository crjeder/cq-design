# Design: thin-region-density-robustness

## Root cause

`_thin_regions` measures wall thickness for a stride-subsampled set of faces and leaves
every other face at `inf`. `is_thin` is therefore true only on sampled faces. The grouping
(`measure_stl.py:317-325`) keeps an adjacency edge only when **both** its faces are thin,
then drops components with `< 2` faces. With stride `s = ceil(n_faces / max_samples)`,
sampled faces on one wall are ~`s` triangles apart and almost never share an edge, so the
"both endpoints thin" filter yields almost no edges and every sampled-thin face becomes its
own singleton component -- all dropped. The detector returns `[]` on exactly the dense
meshes the cap is meant to handle.

## Decision 1: Reconnect via barrier flood-fill, not denser sampling

Raising or removing the cap (TODO option 2) is rejected: the ray-cast is a Python loop over
sampled faces, each vectorized over all `n_faces` triangles (`O(samples * n_faces)`).
Letting `samples -> n_faces` makes it `O(n_faces^2)` -- minutes on a 50k-face mesh. The cap
must stay.

One-hop dilation of `is_thin` to unsampled neighbors (TODO option 1, literal form) only
reconnects faces up to two hops apart, i.e. stride `s <= 2`. For a 30k-face mesh `s = 10`,
so one-hop is insufficient -- it would still fragment.

Instead, change the **grouping**, not the sampling. Treat sampled-thin faces as seeds and
connect two seeds when a path exists between them through the full mesh adjacency graph that
does not cross a **confirmed-thick** face (a face that was sampled and measured at or above
`thin_max`). Unsampled faces (unknown thickness) are transparent to the flood; confirmed-thick
faces are barriers. Concretely:

1. `thin_seed` = sampled faces with `thickness < thin_max` (today's `is_thin`).
2. `barrier` = sampled faces with `thickness >= thin_max` (confirmed thick).
3. Build connectivity over all faces using `mesh.face_adjacency`, dropping any edge incident
   to a `barrier` face. Run `_union_find` over the remaining edges (reusing the existing
   helper).
4. Group the `thin_seed` faces by their component id. A physical thin wall's stride-spaced
   seeds now land in one component because the unsampled faces between them are transparent.

This is robust to any stride and stays `O(n_faces)` (one union-find over adjacency edges);
the expensive ray-cast is untouched.

## Decision 2: Statistics come from measured faces only

Region thickness/centroid/direction must stay grounded in real measurements. After grouping,
each region's stats (`thickness_mm`, `thickness_mean_mm`, `thin_direction`, centroid,
`brittle`) are computed from that component's **seed** faces (the sampled-thin ones, which
have a measured `thickness` and reliable normals), exactly as today -- never from the
transparent unsampled faces. So reported numbers are unchanged in kind; only the grouping
that decides which seeds belong together changes.

## Decision 3: Keep the >= 2 region floor, now meaningful

The current `len(comp) < 2` guard suppresses single-face noise. Keep a floor of two
**seed** faces per region. With barrier flood-fill a real wall reliably contributes >= 2
seeds even at high stride (the seeds reconnect), so the floor no longer drops real regions --
it only filters a lone spurious thin measurement, which is its intent.

## Decision 4: Small meshes are unchanged

When `n_faces <= max_samples` every face is sampled, so there are no transparent unknown
faces: every adjacency edge is between two measured faces, the barrier-flood grouping reduces
to the current "both endpoints thin" grouping (thin-thin edges survive, thin-thick and
thick-thick edges are dropped as barriers), and the same components result. The change is a
no-op below the cap, satisfying the "small meshes unchanged" requirement.

## Test approach

- Build one thin-wall fixture (e.g. a 2 mm fin on a block) at a coarse tessellation (< cap)
  and a subdivided copy (> cap, via `mesh.subdivide()` to exceed `max_samples`); assert both
  report the fin region with comparable `thickness_mm`. The subdivided case is the regression
  guard.
- A uniformly thick dense mesh (> cap) still reports no regions.
- Optionally force a tiny `max_samples` in the call to exercise the high-stride path quickly
  without huge meshes.
