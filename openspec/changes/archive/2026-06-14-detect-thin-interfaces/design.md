## Context

FDM parts are weakest across the layer bond, so the failure mode that matters is a thin cross-section carrying load along Z. The skill's only current detector, `_check_thin_walls` in `run_cadquery_model.py`, computes one fill-ratio over the whole part. That is an aggregate: it averages a thin fin against the mass next to it, reports no location, and reports no cause. The agent that must act on the signal is the same agent that wrote the CadQuery script, so a usable signal has to be localized, quantified against print reality, and traceable to either a parameter (it can edit) or a feature (it can reason about).

`measure_stl.py` already extracts `flat_faces` and `cylinders` with `numpy + trimesh` only, and the wrapper already emits a typed `errors[]` contract. This design extends those, it does not introduce a parallel system.

## Goals / Non-Goals

**Goals:**
- Detect thin regions *and the direction of their thinness*, without being fooled by adjacent thick mass. Thinness is a printability problem only when the thin direction lies in the build (XY) plane (each printed layer is a 2D XY slice); a region thin only along Z is a flat, well-bonded slab and is benign for printing.
- Solve attribution where it is cheap (script level) and provide a best-effort location-to-feature map where it is not (geometry level).
- Emit findings through the existing `errors[]` and `geometry` JSON keys; aggregate in `quality_gate.py`.
- Keep the dependency footprint at the current `trimesh + numpy`.

**Non-Goals:**
- No medial-axis skeletonization or full CAD thickness-analysis engine.
- No 2D distance-transform-per-slice path (would add a scipy call per slice); deferred.
- No automatic geometry repair - the skill reports and hints, the agent edits the script.
- No change to the BUILD_PLAN schema beyond reading per-block extents that are already present.

## Decisions

**Local thickness via ray-cast, not area or bbox.** A cross-section area `A(z)` and a feature bounding box are both aggregates and both miss a thin fin beside a thick blob (the fin contributes little to area and nothing to `min(extent)` of the merged part). The local quantity that does not lie is per-point material thickness: for sampled surface points, shoot a ray inward along the inverse normal and measure the distance to the far wall (`mesh.ray.intersects_location`). This is what CAD thickness-analysis does. Alternative considered: `2*area/perimeter` (hydraulic radius) per slice - cheap but still a slice aggregate, fooled by a blob+fin slice; rejected as the sole signal.

**Thinness is classified by direction relative to Z, not just magnitude.** A printed layer is a 2D slice in the XY plane, so a thin region only fails *printability* when its thin direction lies in that plane. Each thin region carries the direction of minimum thickness - in practice the normal of the bounding faces. Classify by `|n . z_hat|`: near 0 means thin in XY (flag in the current pose); near 1 means thin only along Z (a flat, well-bonded slab - benign). This is why a 1 mm plate lying on the bed must not be flagged, and it is cheap because `face_normals` are already computed. Mechanical weakness of thin-in-Z features (bending/peel along a layer line) is out of scope here - this detector is about thin-wall printability.

**Reorientation is a first-class remedy, because thinness is pose-dependent.** The same geometry is a thin wall in one pose and a flat slab in another. For an XY-thin region the detector reports the rotation that would bring the thin direction parallel to Z (lay it flat) as a suggested remedy, alongside thicken and fillet. It is *suggested*, not automatic: laying a wall flat can trade a thin-wall problem for an overhang/bridging problem (e.g. a vertical neck rotated horizontal), and a single rotation rarely fixes every thin region at once, so the hint flags the tradeoff rather than asserting a fix.

**Two levels, because attribution is free at the script level and lost at the mesh level.** Script-level `min(block.extents) < wall_min` knows the block id and the parameter, runs before meshing, and covers *intended* thinness. The geometry level is the safety net for *emergent* thinness - the sliver a union or cut leaves that no parameter names. Splitting this way means the expensive, attribution-poor path only earns its keep on emergent cases.

**Snap emergent findings to the nearest detected feature.** A bare `xyz` is weak for the agent. Reusing the `flat_faces`/`cylinders` `measure_stl` already computes, each geometry-level finding is snapped to the nearest feature within a radius, giving the agent a named handle. Null when nothing is near, rather than dropping the finding.

**Remedy hint keyed to which level and which threshold fired.** Sharp shoulder (steep thickness gradient) -> fillet; flat-and-thin -> thicken; load along Z -> reorient; below ~4 line widths -> all-perimeter/brittle. Thresholds derive from extrusion line width and layer-bond strength, not magic numbers.

## Risks / Trade-offs

- [Ray-cast cost per part-loop iteration] -> Sample a bounded set of surface points (vertices or face centers, capped), not a dense grid; the wrapper already tolerates a few seconds per run.
- [Ray-cast misses thinness between sample points] -> Acceptable as a gate that flags rather than guarantees; script-level check covers the predictable cases exactly.
- [Snap-to-feature picks a misleading feature] -> Report the distance to the snapped feature so the agent can judge confidence; null beyond the radius.
- [Threshold tuning produces false positives that stall the part loop] -> Findings are advisory in the `geometry` block; only crossings of the FDM-grounded threshold become `thin_interface` errors, mirroring how `_check_thin_walls` gates today.
- [Superseding `_check_thin_walls` changes existing test expectations] -> The fill-ratio test is replaced by neck/fin/sliver fixtures; documented in tasks.

## Open Questions

- Exact sampling density and cap for the ray-cast pass. Resolved for now: sample face centers, cap at `max_samples` (default 2000), one inward ray per sampled face.
- ~~Whether the script-level check reads extents from `BUILD_PLAN.json` or inventory~~. Resolved: the schema's `blocks_needed` items now accept an object form `{name, extents_mm}`; the check runs in `plan_validate.py` as a non-failing advisory finding. Inventory descriptors are not used (they describe block types, not instance sizes).
- Default `wall_min_mm` and the line-width multiplier for the brittle threshold (nozzle-dependent). Resolved: `--wall-min`/`--line-width` are wrapper args; `quality_gate.py` derives line width as nozzle x 1.1; the brittle threshold is 4 x line width.

## Implementation Note

The geometry-level thickness uses a vectorized Moeller-Trumbore ray cast in numpy (`measure_stl._ray_thickness`) rather than `trimesh.ray.intersects_location`, because the trimesh ray engine requires `rtree` (a new dependency the design excludes). Behaviour is the same: one inward ray per sampled face, nearest forward hit = wall thickness.
