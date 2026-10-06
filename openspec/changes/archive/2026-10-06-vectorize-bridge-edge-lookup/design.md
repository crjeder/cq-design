## Context

Profile after the previous changes (205 poses over two parts, 154,518 `_is_bridge` calls):

- `_is_bridge`: 401 s cumulative, 363 s own time. The `lookup` dict comprehension at the top runs once per `overhang_regions` call (once per pose) over every adjacency edge; Python 3.12 inlines comprehensions, so it is counted as `_is_bridge`'s own time. The per-region loop adds `verts[e].mean` (212k calls, 21 s) and per-edge scalar numpy work.
- `area_faces`: 13 s over 209 calls, of which about 10 s is `triangles_cross`. Areas do not change under a rigid transform.
- `bed_contact_mask`: 18 s over 615 calls (3 per pose), each recomputing the same mask.

How much of the 363 s is the dict build versus the per-region loop is not separable from a function-level profile; task 1.1 measures it before choosing how far to go.

## Goals / Non-Goals

**Goals:**
- Remove per-edge Python work from the bridge test and the per-pose dict build.
- Compute pose-invariant face areas and the per-pose bed mask once.
- Keep every score and bridge decision identical.

**Non-Goals:**
- Reducing the number of candidate poses scored (separate change; it alters which poses are fully scored).
- Vectorizing across regions (one `_is_bridge` call per region stays).
- The quality-gate, kinematic and preview items in `TODO.md`.

## Decisions

- **Sorted edge keys, not a cached dict.** Encode each adjacency edge as `a * n_vertices + b` (int64, `a < b`), sort once per call, and look region boundary edges up with `searchsorted`. Building is a vectorized sort of the adjacency edges, so it needs no cross-pose cache, which trimesh clears on transform for any custom key. Alternative: cache the dict across poses on the base mesh; rejected because the cache would not survive `apply_transform` and the dict build is still slow when it does run.
- **Vectorize the boundary-edge loop per region.** For a region, the arrays `edges`, `owner`, `boundary` already exist; compute `pair` via `searchsorted`, `other` via a vectorized select, drop in-region and rising-lip edges with masks, transform edge midpoints with `to_rect` in one matrix product, bin to the 4 sides with `np.bincount(weights=length)`. Same arithmetic as the loop, in the same order of tests.
- **Base areas, set once.** Compute `base.area_faces` before the candidate loop and place it in each posed copy's cache after `apply_transform`. Alternative: thread an `area` array through `support_cost`/`overhang_regions`; rejected as a wider signature change for a value trimesh already exposes. Test asserts the injected areas equal a fresh `posed.area_faces`.
- **Bed mask computed once per pose** in the candidate loop and passed to the three helpers that each recomputed it.

## Risks / Trade-offs

- [Vectorized loop changes a bridge decision at a tie, for example summing edge lengths in a different order] -> compare `overhang_regions` bridge flags and `support_cost` on the fixture meshes and on the tray mesh before and after; flags must be identical.
- [Injecting into trimesh's cache relies on its cache API] -> covered by the equality test; falls back to recomputation if the key is wiped.
- [Edge key overflow] -> `n_vertices` squared stays far below int64 for any printable mesh.
