## Context

`quality_gate._analyze_stl` loads the part STL with trimesh, applies the accepted print orientation's `rotate`, then checks watertightness and overhang. It never inspects how adjacent triangles meet. The reproducer (`step_rim_fillet.py`, 9252 triangles) showed the signal is trivially visible in that data: `trimesh.face_adjacency_angles` returns 179.7 degrees at four places and about 135 degrees at four more, all at `r` near 154 mm, `z` near 87.5 to 88 mm. Sanity data from ordinary geometry (cups, filleted discs, rounded rectangles, revolves, stadium walls, holes, tapered walls; 0.5 to 3 mm fillets): the only sharp adjacencies were the real 90 degree corners; none exceeded 90.

## Goals / Non-Goals

**Goals:** flag near-zero-thickness fins and knife-edge folds in the delivered mesh; report where; point at the likely cause; add no dependency; leave current outputs unchanged for parts without folds.

**Non-Goals:** repairing geometry; detecting fins that a tessellator would smooth over (there are none, folds survived 75x refinement); triangle-quality metrics; changing tessellation settings.

## Decisions

- **Interior dihedral, not aspect ratio.** Thin planar faces (0.6 mm rib chamfers, 160 mm long) give aspect ratios in the thousands and are harmless. A fin is characterised by two neighbouring faces whose normals nearly oppose. Alternative: flag by triangle aspect ratio or minimum area; rejected, 911 harmless triangles trip it in the reproducer while the four real defects are 0.0126 mm2.
- **Mesh check, not a B-Rep check.** Same layer as `non_watertight`/`overhang_exceeded`, operates on the file that reaches the slicer, needs no CadQuery. Alternative: inspect B-Rep face adjacency with OCC; rejected as heavier and blind to defects the tessellator introduces.
- **Threshold 10 degrees interior (170 degrees between normals).** The defects were 0.3 and 45 degrees interior; ordinary geometry never went below 90. A tapered rib tip of about 21 degrees (the reproducer's own rib) must not trip it. The threshold is a module constant `FOLD_MIN_INTERIOR_DEG` in `mesh_io.py`. Validated: 15 golden/fixture STLs, none flagged, sharpest legitimate interior angle 41.2 degrees (phone-stand).
- **Cluster, don't spam.** A fin is many adjacent triangle pairs along one seam. Cluster fold pairs by proximity (union-find on shared vertices) and report count of clusters, worst angle, worst location and smallest face area, capped to the five sharpest locations.
- **`warning`, not `error`.** A slicer may or may not draw the fin, and the threshold has only been checked on 15 small STLs and one reproducer. An `error` tier for sub-1-degree folds was rejected: the reproducer's sharpest fold is 1.4 degrees at export tolerance.
- **Build-frame location.** The mesh is already rotated before checks; reuse it so the location matches `overhang_exceeded`.
- **Where the code lives.** `mesh_io.fold_metrics` beside `overhang_metrics`, so `print_orientation.py` or a future gate can reuse it and it is unit-testable on a hand-built trimesh without CadQuery.

## Risks / Trade-offs

- [False positive on a legitimate knife edge, for example a razor-thin taper, a wedge tip, or a cone apex] -> advisory only; the finding carries the location and angle so a deliberate feature can be recognised; threshold validated on the corpus first.
- [Misses fins between non-adjacent faces, or two solids touching only at a vertex] -> accepted; this targets the observed class (shared-edge folds).
- [Coarse tessellation of a very sharp convex curve reads as a fold] -> not seen in any measured case; adjacent facets on a curve differ by the angular tolerance (about 6 degrees), far from 170.
- [Fix loop acts on a warning it cannot fix] -> hint is specific; if the LLM edits blindly the next gate run shows whether the count dropped.

## Open Questions

- Resolved: no `error` tier (the reproducer's sharpest fold is 1.4 degrees at export tolerance); per-part gate pass only, consistent with overhang.
- Open: promote `sliver_fin` to a `fix`-routed action so the builder acts on it, once real runs show no false positives.
