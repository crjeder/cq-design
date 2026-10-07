## Why

A profile of the Silica-tray orientation run (492 s) puts 401 s inside `mesh_io._is_bridge`, 363 s of it in the function's own code. After the earlier hash and topology-cache changes, this is now about 80% of the run. `_is_bridge` rebuilds a Python dict of every mesh edge (`ctx["lookup"]`) once per candidate pose, although the edge-to-face map is pure connectivity, and it then walks region boundary edges in a per-edge Python loop (212k `verts[e].mean` calls, 21 s). Smaller repeated work remains in `print_orientation`: `area_faces` (13 s, rotation-invariant but recomputed per pose) and `bed_contact_mask` (18 s, computed 3 times per pose).

## What Changes

- Replace the per-call dict edge lookup in `_is_bridge` with sorted integer edge keys and `np.searchsorted`, built vectorized once per `overhang_regions` call.
- Vectorize the boundary-edge loop in `_is_bridge` (other-face lookup, region and rim tests, rectangle-side binning, covered length per side) with numpy masks.
- In `optimize_orientation`, compute face areas once on the base mesh and reuse them for every pose, and compute `bed_contact_mask` once per pose and pass it to `_support_metrics`, `_gentle_incline_fraction` and `_stability_metrics`.
- No change to which orientation is chosen, to scores, or to the bridge decision for any region.

## Capabilities

### New Capabilities

### Modified Capabilities
- `overhang-analysis`: adds a requirement that bridge detection cost is not dominated by per-edge Python work.
- `print-orientation-optimization`: adds a requirement that pose-invariant data and the bed-contact mask are computed once rather than per use.

## Impact

- `src/mesh_io.py` (`_is_bridge`, `overhang_regions`), `src/print_orientation.py` (`optimize_orientation` and the three metric helpers' signatures).
- Internal signatures only; `support_cost`, `overhang_metrics` and the quality-gate JSON contract are unchanged.
- No new dependencies.
