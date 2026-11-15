## Context

`optimize_orientation` builds ~112 candidate bed-down normals and, for each, copies and rotates the whole mesh, then runs `support_cost` (connected components of overhang faces plus `_is_bridge` per region), bed contact, gentle-incline and stability. Measured on the Silica-tray tray (1,292,626 faces): 53.5 s total, ~0.4 s per exact support evaluation. Retention posts (~530 cones plus base cylinders) at cadquery's default STL export tolerance (0.1 mm linear, 0.1 rad angular) supply most faces.

Key fact: bridge detection only multiplies a region's cost by `BRIDGE_COST_FACTOR` (0.1), so `0.1 x raw <= exact <= raw`, where raw is the support cost with no region analysis (faces with `nz < 0`, angle over the limit, not bed contact). Raw needs only face normals, areas, centroid z and the bed plane. On the tray it takes 3.6 s for all 112 candidates, and every non-identity candidate's lower bound exceeds the identity pose's exact cost (42.2).

## Goals / Non-Goals

**Goals:**
- Same selected orientation and reported scores as exhaustive scoring.
- Cut exact evaluations to the few candidates that can still win.
- Keep a progress indicator (already added).

**Non-Goals:**
- Changing scoring formulas, bands, or selection order.
- Per-instance geometry handling for copied features (posts); no instance data reaches the mesh.
- Parallelism, caching across runs.

## Decisions

1. **Vectorized pre-pass over all candidates.** Per candidate from `R[2,:3]`: `nz = N @ rz`, `cz = C @ rz`, `min_z` from convex-hull vertices (extent of a convex set), build height from hull vertices, bed-contact mask, raw support cost, gentle-incline fraction, strength, and cosmetic-down. No `mesh.copy()` or `apply_transform` per candidate. Chunk candidates if memory requires. Alternative: keep the per-candidate mesh copy and only skip `support_cost`; rejected, copy and normals recompute are a large share at 1.3M faces.
2. **Bounds then ordered exact evaluation.** `LB = BRIDGE_COST_FACTOR x raw`, `UB = raw`. Evaluate exactly in ascending `(LB, idx)` order. Stop when the next `LB` is strictly greater than the incumbent's key. Equal bounds are evaluated (ties decided by later keys). Alternative: only prune against `UB` of the best; weaker, so rejected.
3. **Per-mode pruning.** Support is pruned directly in `min_support` and as the strength-band tiebreak in `strength`. For `visual_quality`, `min_build_height` and `min_print_time`, support is only a tiebreak after a banded primary key, so contenders are fixed by the cheap primary key first and support is bounded only among them. Stability is cheap (contact faces only) and computed for all candidates, since the stable-only filter precedes every mode's ordering.
4. **Reuse `_select` unchanged.** Pruned candidates are left out of the list handed to `_select`; the evaluation order guarantees the dropped ones could not be chosen. An exhaustive mode (`prune=False`) keeps the old path for the equivalence test.
5. **Coarser scoring tessellation as a separate, opt-in parameter.** `orientation_for(..., tolerance, angular_tolerance)`; default unchanged. Flip the default only after a fixture sweep shows identical selections. Alternative: coarse-rank then full-res rescore of top K; deferred until the tolerance sweep shows it is needed.

## Risks / Trade-offs

- [Bounds wrong if the exact cost uses faces the raw pass excludes, e.g. a different bed mask] -> Share one bed-contact definition (`bed_contact_mask` logic) between the pre-pass and the exact path; the equivalence test covers every mode.
- [Floating-point differences between vectorized and per-candidate values flip a tie] -> Use the same operations in the pre-pass, compare against the incumbent with a small epsilon on the safe side (evaluate when within epsilon), and round reported values as now.
- [Coarser tessellation shifts curved-face normals, flipping a 45 deg overhang call] -> Opt-in only; validate on fixtures before changing the default.
- [Little pruning on parts with many near-equal candidates] -> Falls back to exhaustive cost; never worse than today apart from the pre-pass (a few seconds at 1.3M faces).

## Results

- Silica-tray tray (1,292,626 faces, 112 candidates): 53.5 s -> 12-15 s (`strength` and `min_support`), identical pose and scores. Remaining floor: ~6 s pre-pass over all candidates plus ~4 s one-time mesh setup (adjacency, edge lookup, convex hull, center of mass).
- Tessellation sweep (6 curved CadQuery parts, defaults vs 0.05/0.3, 0.1/0.3, 0.2/0.5 mm/rad): chosen orientation identical in every case, faces 3-7x fewer, but the reported support score drifts (up to 19%, filleted box 42.4 -> 50.5). Linear tolerance had no effect once the angular tolerance was 0.3 (angular dominates). Decision: coarse tessellation stays opt-in; with pruning, tessellation is no longer the dominant cost.
