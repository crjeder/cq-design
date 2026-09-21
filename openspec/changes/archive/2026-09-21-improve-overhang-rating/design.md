## Context

`overhang_metrics` and `support_cost` (src/mesh_io.py) iterate faces independently. Consequences:
short bridges look like overhangs; cost scales with triangle count in curved regions; the gate
flips a warning on/off at exactly `overhang_deg` (cliff); bed contact is a hard height band.
print_orientation.py ranks candidates by `support_cost`, so these artifacts change the selected pose.

## Goals / Non-Goals

**Goals:** bridges of span <= `bridge_max_mm` are not overhangs; rating is tessellation-invariant, continuous in angle, and deterministic; existing JSON keys keep name and meaning.
**Non-Goals:** slicer-accurate support volume (NSV), area-cumulation candidates, `min_build_height` mode, anchoring analysis via ray casting.

## Decisions

1. **Region grouping.** New helper `overhang_regions(mesh, overhang_deg, exclude_mask)` in mesh_io: select down-facing faces past the limit, label connected components via `trimesh.graph.connected_components` on face adjacency restricted to the selected faces. Returns per-region area, mean angle, face indices. Area is a plain face-area sum, so already tessellation-invariant; grouping is needed for bridge span and per-region reporting.
2. **Bridge test.** A region is a bridge when all hold: mean angle >= `BRIDGE_MIN_DEG` (80, near-horizontal ceiling); its shortest in-plane extent (short side of the XY oriented bounding rectangle, via PCA of vertices projected on XY) <= `bridge_max_mm`; and it is supported on at least two sides. Support is read from the mesh, no ray casting: a region boundary edge is *anchored* when the face across it is not itself a down-facing over-limit face and not a free lip, i.e. it is a wall or up-facing face (`nz > -sin(overhang_deg)`) sharing that edge. Each anchored boundary edge is assigned to the nearest of the 4 sides of the oriented rectangle by its outward XY direction; the region is supported when anchored edges cover >= 2 distinct sides (anchored length per side must be >= 50% of that side's length, so a single tiny contact does not count). A cantilever anchored on one side, or a tab tip, is therefore an overhang regardless of its width.
3. **Cost.** `support_cost` uses a per-region ramp `((angle - limit)/(90 - limit)) ** OV_H` (`OV_H` = 2.0, the existing `SUPPORT_EXPONENT` renamed, alias kept). It is zero at the limit, so continuous there. Bridge regions contribute `BRIDGE_COST_FACTOR` (0.1) of normal cost, not 0, so orientation still mildly prefers fewer bridges.
4. **Bed contact.** One shared helper using `FIRST_LAYER_BAND_MM`, used by both `overhang_metrics` (currently its own `BED_CONTACT_BAND_MM` copy) and `print_orientation._bed_contact_mask`.
5. **Determinism.** Sort candidate normals by a fixed key (rounded components) before tie-band selection; round scores to 6 decimals.
6. **Profile.** `constraints.bridge_max_mm`, optional, 10.0 when absent, so existing profiles still validate. `quality_gate` and `print_orientation` read it and pass it to mesh_io.

## Risks / Trade-offs

- Golden orientation results may change on parts with short bridges: inspect evals, regenerate only if justified.
- Side assignment uses the oriented rectangle, so strongly non-rectangular regions (ring-shaped ceilings) may be misjudged; the 50% side-coverage rule keeps this conservative (falls back to overhang).
- 10 mm is a typical FDM PLA bridge limit; tune per printer.
