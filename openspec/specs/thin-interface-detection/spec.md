# Thin Interface Detection

## Purpose

Defines requirements for detecting thin walls and interfaces in generated models, both before meshing (script-level block-extent checks against the wall minimum) and after meshing (geometry-level local thickness fields with build-direction classification). Thin regions are mapped to named features, reported as typed FDM-thresholded errors with remedy hints, surfaced in the wrapper `geometry` block, and aggregated by the quality gate.

## Requirements

### Requirement: Script-level block-extent thinness check
Before meshing, the skill SHALL flag any planned block whose smallest extent is below the configured wall minimum, attributing the finding to the block id and the parameter responsible. This catches intended thinness with full attribution and no mesh cost.

#### Scenario: A block is thinner than the wall minimum
- **WHEN** a block in `BUILD_PLAN.json` has a smallest extent (e.g. width 1.2 mm) below `wall_min_mm`
- **THEN** the skill reports a finding naming the block id, the offending dimension and its value, and the `wall_min_mm` it crossed, before any STL is produced

#### Scenario: All blocks are thicker than the minimum
- **WHEN** every block's smallest extent is at or above `wall_min_mm`
- **THEN** the script-level check produces no findings

### Requirement: Geometry-level local thickness field with direction classification
The skill SHALL compute a local material thickness at sampled points over the STL surface, together with the direction of minimum thickness, so that a thin region is detected regardless of the size of adjacent masses. The skill SHALL classify each thin region by whether its thin direction lies in the build (XY) plane or along the build (Z) axis, because a printed layer is a 2D XY slice and thinness is a printability problem only when the thin direction lies in that plane. A region thin only along Z (a flat, well-bonded slab) SHALL NOT be flagged as a thin-wall printability problem. Aggregate measures (cross-section area, part bounding box) SHALL NOT be used as the sole thinness signal.

#### Scenario: Thin vertical fin beside a thick mass
- **WHEN** a part contains a 2 mm fin standing vertically (thin direction in the XY plane) attached to a 20 mm block
- **THEN** the thickness field reports the fin region at ~2 mm, classified as thin-in-XY, even though the cross-sectional area and part bounding box are dominated by the block

#### Scenario: Flat slab thin only along Z
- **WHEN** a part contains a 1 mm plate lying flat on the bed (thin direction along Z)
- **THEN** the region is classified as thin-in-Z and is NOT flagged as a thin-wall printability problem

#### Scenario: Thin neck across the build direction
- **WHEN** two masses are joined by a narrow neck whose thin direction lies in the XY plane
- **THEN** the thickness field reports the neck region with its measured thickness, direction, and location

#### Scenario: Uniformly thick part
- **WHEN** every region of the part is at or above the thickness threshold
- **THEN** no thin-region findings are produced

### Requirement: Emergent thin regions are mapped to the nearest named feature
Each geometry-level thin region SHALL be reported with its `xyz` location and snapped to the nearest detected feature (`flat_face` or `cylinder` from `measure_stl`) so the agent can map a thin region with no governing parameter back to a feature it can edit.

#### Scenario: Sliver left by a boolean
- **WHEN** a union or cut leaves a thin sliver that no single block parameter describes
- **THEN** the finding includes the sliver's `xyz` location and the id/label of the nearest detected feature

#### Scenario: No feature near the thin region
- **WHEN** a thin region has no detected feature within the snap radius
- **THEN** the finding reports the `xyz` location with the nearest-feature field left null rather than omitting the finding

### Requirement: Thin regions are reported as a typed, FDM-thresholded, remedy-typed error
When a thin region crosses its threshold, `run_cadquery_model.py` SHALL emit a `thin_interface` entry in the `errors[]` contract carrying location, `thickness_mm`, `equiv_diameter_mm`, the threshold crossed, the thin direction (and whether it lies in XY or along Z), and a remedy `hint` keyed to which level fired. Thresholds SHALL be grounded in FDM reality (extrusion line width), not arbitrary constants.

#### Scenario: XY-thin region with a reorientation that lays it flat
- **WHEN** a region is thin in the XY plane and a rotation exists that would bring its thin direction parallel to Z
- **THEN** the hint offers that reorientation as a suggested remedy and flags that it may trade the thin wall for an overhang, rather than asserting a guaranteed fix

#### Scenario: Region thinner than the infill threshold
- **WHEN** a region's `equiv_diameter_mm` is below roughly four extrusion line widths
- **THEN** the hint flags the region as all-perimeter/brittle and recommends thickening past the infill threshold

#### Scenario: Script-level finding remedy
- **WHEN** the thin region was found by the script-level block-extent check
- **THEN** the hint names the block and parameter to increase

### Requirement: Findings are surfaced in the geometry block and aggregated by the quality gate
Thin-region findings SHALL appear in the `geometry` block of the wrapper JSON so the agent can reason over them directly, and `quality_gate.py` SHALL include them in its aggregated DFM report alongside overhang and printability results.

#### Scenario: Agent reads findings from wrapper JSON
- **WHEN** `run_cadquery_model.py` completes a run that found thin regions
- **THEN** the `geometry` block lists each thin region with its thickness, location, and nearest feature

#### Scenario: Quality gate aggregates thin-interface findings
- **WHEN** `quality_gate.py` aggregates DFM results for a part with thin regions
- **THEN** the report includes the thin-interface findings together with the in-process trimesh overhang and geometry results

### Requirement: Thin-region detection is robust to mesh triangle density

The geometry-level thin-region detector SHALL report a contiguous thin wall regardless of how
finely the part is tessellated. Subsampling the local-thickness ray-cast for performance SHALL
NOT cause a thin wall to go unreported on meshes whose face count exceeds the sample cap: a
thin wall reported on a coarse mesh SHALL still be reported when the same wall is remeshed to
more faces than the cap. The detector SHALL preserve the ray-cast performance bound (the
number of thickness rays stays bounded by the sample cap; the per-face thickness pass SHALL
NOT scale with the square of the full face count), and each reported region SHALL keep its
existing fields (thickness, thin direction, XY/Z orientation, location, nearest feature,
brittle flag), computed from measured faces.

#### Scenario: Thin wall on a mesh above the sample cap is still reported
- **WHEN** a part with a thin wall (thin direction in the XY plane) is tessellated to more
  faces than the ray-cast sample cap
- **THEN** the detector still reports that wall as a thin-in-XY region with its measured
  thickness, rather than returning no thin regions

#### Scenario: Result is stable across tessellation density
- **WHEN** the same thin-walled part is measured at a coarse tessellation (at or below the
  cap) and at a fine tessellation (above the cap)
- **THEN** both measurements report the thin wall as a region with comparable thickness, so
  the finding does not depend on triangle count

#### Scenario: Uniformly thick dense mesh reports nothing
- **WHEN** a part whose every region is at or above the thickness threshold is tessellated to
  more faces than the cap
- **THEN** the detector reports no thin regions (the density-robust grouping does not
  manufacture spurious regions from unsampled faces)

### Requirement: Ray-cast pre-filtering does not change reported thickness
Any optimization that restricts which triangles a thickness ray is tested against (such as a facing or in-front half-space filter) SHALL produce the same per-face thickness as testing every triangle, for watertight meshes, within floating-point tolerance. The wrapper JSON contract and region fields SHALL be unchanged.

#### Scenario: Filtered and unfiltered casts agree
- **WHEN** the thickness of every sampled face of a watertight part is computed with the pre-filter and with the unfiltered cast
- **THEN** the two thickness arrays are equal within tolerance

#### Scenario: Thin-region output is unchanged
- **WHEN** the existing thin-interface fixtures are measured after the change
- **THEN** the reported regions, thicknesses, and orientations match the previous results
