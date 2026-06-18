## Why

FDM parts fail at thin cross-sections loaded across the layer bond - the weakest axis - yet the skill has no reliable detector for them. The current `_check_thin_walls` is a single fill-ratio heuristic over the whole part: it misses a thin neck or fin inside an otherwise chunky model, and it cannot tell the agent *where* the thin region is or *what* produced it. The agent writes the CadQuery script, so a thin-region signal is only actionable if it is localized, quantified against FDM reality, and mappable back to a parameter or feature it can edit.

## What Changes

- Add a **local thickness** detector that finds thin regions anywhere in a part, independent of orientation, instead of the single whole-part fill-ratio guess. Aggregate measures (cross-section area, part bounding box) average over a region and hide a thin fin next to a thick mass; a per-point thickness field does not.
- Run detection at **two levels** so attribution is solved where it is cheap:
  - **Script/plan level**: flag any block whose smallest extent is below the wall minimum (`min(block.extents) < wall_min`). Intended thinness, with perfect attribution to the block and parameter, before meshing.
  - **Geometry level**: a local thickness field over the STL as the safety net for *emergent* thinness - the sliver left by a union or cut that no parameter describes. Reports `{thickness_mm, xyz, nearest_feature}` by snapping the thin region to the closest detected `flat_face`/`cylinder` from `measure_stl`.
- Emit a typed `thin_interface` error through the existing `run_cadquery_model.py` `errors[]` contract: location, `thickness_mm`, `equiv_diameter_mm`, the FDM threshold it crossed, load axis, and a remedy hint keyed to which level fired (bump parameter / add fillet / reorient / thicken past the infill threshold).
- Surface the thin-region findings in the `geometry` block of the wrapper JSON so the agent can reason over them directly, and aggregate them in `quality_gate.py` alongside overhang and orca-check results.

## Capabilities

### New Capabilities
- `thin-interface-detection`: Two-level detection of thin, weak regions in a part (script-level block-extent check with full attribution, plus a geometry-level local thickness field for emergent thinness), reported as structured, FDM-thresholded, remedy-typed signals that an agent can act on without re-deriving the cause.

### Modified Capabilities
<!-- The thin_interface error is a new instance emitted through the existing generic errors[] contract governed by `structured-errors`; it adds no new requirement to that spec, so no delta is needed. -->

## Impact

- `src/measure_stl.py`: add the local-thickness field (trimesh ray-cast over sampled surface points) and the snap-to-nearest-feature mapping; reuses the existing `flat_faces`/`cylinders` detection.
- `src/run_cadquery_model.py`: replace/augment `_check_thin_walls` to emit the typed `thin_interface` error and add thin-region findings to the `geometry` block; the JSON contract keys are extended, not renamed.
- `src/quality_gate.py`: include thin-interface findings in the aggregated DFM report.
- `reference/FDM 3D Print Design Guidelines.md`: rewrite the `Print Orientation > General Orientation Rules` section to state the priority order (stability first, then minimize overhangs/support) and the contradiction fallback (if no orientation satisfies both, split the part and escalate to planning). This is the durable, cross-finding policy the LLM applies when resolving the reorientation tradeoff this change surfaces; it is reference content, not detector output. Injected into `planning.md` and `part.md` via `{{FDM_GUIDELINES}}`.
- Plan-level check needs access to per-block extents from `BUILD_PLAN.json` / `blocks/inventory.json`.
- Dependencies: trimesh ray-casting is already available (no new dependency for the 3D path); a 2D distance-transform variant would add a scipy call per slice and is out of scope for this change.
- `tests/`: new coverage for thin-neck, thin-fin, and emergent-sliver fixtures; the existing fill-ratio test is superseded.
