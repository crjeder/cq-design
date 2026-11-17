# overhang-analysis Specification

## Purpose

Define how the quality gate performs overhang and printability analysis on exported
STL geometry entirely in-process (trimesh + numpy, no external slicer or MCP), how
overhang faces are detected relative to the plan overhang limit, and how findings are
reported using the structured quality gate issue contract.
## Requirements
### Requirement: Overhang analysis runs in-process via trimesh with no slicer or MCP

The quality gate SHALL perform overhang and printability analysis on the exported
STL entirely in-process using trimesh and numpy. The analysis SHALL NOT invoke an
external slicer (e.g. OrcaSlicer), the orca-check MCP, the scad-analyzer MCP, or
any other external process or network service.

#### Scenario: Analysis completes offline
- **WHEN** the quality gate analyzes an exported STL with no MCP servers and no
  slicer binary available on the system
- **THEN** the overhang analysis still produces its findings using only trimesh
  and numpy, with no external process invoked

#### Scenario: trimesh unavailable degrades to warning
- **WHEN** trimesh or numpy cannot be imported
- **THEN** the analysis emits a single issue with `severity: "warning"` and
  `type: "check_skipped"` and does not raise

### Requirement: Overhang faces are detected relative to the plan overhang limit

The analysis SHALL classify each downward-facing mesh face by its overhang angle
measured from horizontal, and SHALL flag faces whose overhang angle exceeds the
plan's `constraints.overhang_max_deg` (default 45) as requiring support. A face is
downward-facing when its unit normal has a negative Z component; its overhang
angle from horizontal SHALL be computed as `arcsin(min(1, -nz))` in degrees.

#### Scenario: Steep overhang flagged
- **WHEN** a model contains a face whose overhang angle is 60 degrees and
  `overhang_max_deg` is 45
- **THEN** the analysis flags that face as support-needed

#### Scenario: Shallow overhang not flagged
- **WHEN** every downward-facing face has an overhang angle at or below
  `overhang_max_deg`
- **THEN** no overhang issue is emitted and the analysis reports the model as
  self-supporting

#### Scenario: Upward and vertical faces ignored
- **WHEN** a face has a non-negative normal Z component (upward-facing or vertical)
- **THEN** that face is excluded from overhang classification

### Requirement: Faces resting on the print bed are not overhangs

The analysis SHALL exclude faces resting on the print bed from overhang classification:
a steeply down-facing face whose centroid sits within a first-layer-height band of the
mesh's lowest point is resting on the bed, which supports it in place of support
material. In particular a part's flat bottom face (a 90-degree downward face at the
lowest level) SHALL NOT be reported as an overhang. A downward face that sits above that
band (for example the underside of an elevated ledge or internal ceiling) SHALL remain
subject to overhang classification.

#### Scenario: Flat bottom on the bed is not flagged
- **WHEN** a part has a flat bottom face resting on the bed (its centroid at the mesh's
  lowest level) and no other downward-facing faces above the overhang limit
- **THEN** the analysis emits no `overhang_exceeded` issue

#### Scenario: Elevated downward face is still flagged
- **WHEN** a part has a downward-facing face whose overhang angle exceeds
  `overhang_max_deg` and whose centroid sits well above the mesh's lowest level
- **THEN** the analysis flags that face as support-needed even though the part also has a
  flat bottom on the bed

### Requirement: Overhang findings report extent and location

When the analysis flags support-needed overhangs, the emitted issue SHALL include
the total flagged overhang area in mm^2, the worst overhang angle in degrees, and
the location of the worst overhang region as face-centroid coordinates
`[x, y, z]` in mm.

#### Scenario: Issue carries area, worst angle, and location
- **WHEN** support-needed overhangs are detected
- **THEN** the issue includes `overhang_area_mm2` (sum of flagged face areas),
  `worst_angle_deg`, and `location_xyz_mm` (centroid of the flagged face with the
  largest overhang angle)

#### Scenario: Worst region identifies the steepest face
- **WHEN** multiple faces exceed `overhang_max_deg` at differing angles
- **THEN** `location_xyz_mm` corresponds to the face with the largest overhang
  angle and `worst_angle_deg` equals that angle

### Requirement: Overhang findings use the structured issue contract

Overhang findings SHALL be emitted as issue objects matching the existing quality
gate contract: each issue SHALL have `source: "geometry"`, a `severity`, a `type`,
a human-readable `message`, and a `hint`. Support-needed overhangs SHALL use
`type: "overhang_exceeded"`. The default severity for `overhang_exceeded` SHALL be
`warning` so it surfaces in the fix prompt without blocking a clean pass on its own.

#### Scenario: Overhang issue shape
- **WHEN** an overhang issue is emitted
- **THEN** it contains `source`, `severity`, `type`, `message`, and `hint` keys and
  is consumable by the fix-prompt renderer without modification

#### Scenario: Clean model emits no overhang issue
- **WHEN** the model has no support-needed overhangs and is watertight
- **THEN** the analysis contributes no error or warning issues for overhangs

### Requirement: Non-watertight and degenerate meshes are reported as errors

The analysis SHALL emit an error issue when the loaded mesh has no triangles
(`invalid_geometry`) or is not watertight (`non_watertight`), and SHALL emit an
error issue when the STL fails to load (`mesh_load_error`). These error issues
SHALL block a clean pass.

#### Scenario: Non-watertight mesh
- **WHEN** the loaded mesh is not watertight
- **THEN** the analysis emits an issue with `severity: "error"` and
  `type: "non_watertight"`

#### Scenario: Empty mesh
- **WHEN** the loaded mesh has zero faces
- **THEN** the analysis emits an issue with `severity: "error"` and
  `type: "invalid_geometry"` and skips overhang classification

### Requirement: Short bridges are not overhangs
The analysis SHALL group unsupported down-facing faces into connected regions and SHALL classify a near-horizontal region (mean overhang angle >= 80 degrees) whose shortest in-plane extent is at most `constraints.bridge_max_mm` (default 10.0) and that is supported on at least two sides (boundary edges shared with wall or up-facing faces covering at least two distinct sides of the region's oriented rectangle) as a bridge. Bridge area SHALL be reported as `bridge_area_mm2` and SHALL NOT be included in `overhang_area_mm2` or trigger `overhang_exceeded`.

#### Scenario: Short bridge not flagged
- **WHEN** a part has a horizontal ceiling spanning 6 mm between two walls and `bridge_max_mm` is 10
- **THEN** no `overhang_exceeded` issue is emitted and `bridge_area_mm2` is greater than 0

#### Scenario: Long span still flagged
- **WHEN** the same ceiling spans 25 mm
- **THEN** the region counts toward `overhang_area_mm2` and `overhang_exceeded` is emitted

#### Scenario: Short cantilever is not a bridge
- **WHEN** a horizontal ledge 6 mm wide projects from a single wall and is free on its other sides
- **THEN** it counts toward `overhang_area_mm2` and `overhang_exceeded` is emitted

#### Scenario: Ceiling supported on two sides is a bridge
- **WHEN** a horizontal ceiling 6 mm wide is joined to walls on two opposite sides
- **THEN** it is classified as a bridge

#### Scenario: Steep non-horizontal overhang is never a bridge
- **WHEN** a 60 degree overhang region has a shortest extent of 3 mm
- **THEN** it counts as an overhang, not a bridge

### Requirement: Overhang area is independent of tessellation
`overhang_area_mm2` SHALL be unchanged (within 1%) when the same surface is re-meshed with a different triangle density.

#### Scenario: Refined mesh gives same area
- **WHEN** a curved overhang surface is subdivided to 4x the triangle count
- **THEN** `overhang_area_mm2` differs by less than 1%

### Requirement: Overhang region analysis does not re-access mesh properties per region
`overhang_regions` SHALL read the mesh vertex, face and face-area arrays once per call and reuse them for every region, so analysis time does not scale with region count times mesh size through trimesh cache verification.

#### Scenario: Results unchanged
- **WHEN** `overhang_regions`, `overhang_metrics` or `support_cost` runs on any mesh
- **THEN** the regions, bridge flags, areas and costs are identical to those produced before the change

#### Scenario: Many small regions
- **WHEN** a mesh produces thousands of overhang regions
- **THEN** `mesh.vertices`, `mesh.faces` and `mesh.area_faces` are each accessed a constant number of times per call, independent of region count

### Requirement: Bridge detection avoids per-edge Python work
`_is_bridge` SHALL resolve region boundary edges to their neighboring faces and accumulate anchored length per rectangle side with vectorized array operations, and SHALL NOT build a Python mapping over all mesh edges per `overhang_regions` call.

#### Scenario: Results unchanged
- **WHEN** `overhang_regions`, `overhang_metrics` or `support_cost` runs on any mesh
- **THEN** each region's `bridge` flag, area and the resulting costs are identical to those produced before the change

#### Scenario: Setup cost does not scale in Python per edge
- **WHEN** a mesh with 100,000 or more adjacency edges is analyzed
- **THEN** the edge-to-face lookup is built from sorted array keys without a per-edge Python loop or dict

### Requirement: Bridge detection gates regions in bulk
`overhang_regions` SHALL evaluate the bridge angle gate for all regions with one vectorized pass and SHALL invoke the per-region bridge analysis only for regions that pass it, and bridge analysis SHALL NOT compute a convex hull or a row-wise `np.unique` for regions that fail the gate.

#### Scenario: Results unchanged
- **WHEN** `overhang_regions`, `overhang_metrics` or `support_cost` runs on any mesh
- **THEN** each region's `bridge` flag and area, and the resulting costs, are identical to those produced before the change

#### Scenario: Failing regions skip geometry work
- **WHEN** a region's area-weighted mean overhang angle is below `BRIDGE_MIN_DEG`
- **THEN** it is reported with `bridge` false without oriented-bounds or boundary-edge computation


### Requirement: Sacrificial fin unions are excluded from part findings
The gate SHALL skip unions flagged `sacrificial: true` when evaluating
`overhang_exceeded`, `sliver_fin`, thin-region and brim findings, and SHALL emit one
`designed_support` `info` issue giving the fin count and total fin volume. The part
unions SHALL still be analyzed in full.

#### Scenario: Fin gap not flagged
- **WHEN** a plan has a part union and a `sacrificial` fin union with a 0.2 mm standoff
- **THEN** no `sliver_fin` or thin-region finding names the fin union

#### Scenario: Designed support reported
- **WHEN** at least one sacrificial union exists
- **THEN** the report contains exactly one `designed_support` info issue

#### Scenario: Part overhang still reported
- **WHEN** the part union has an overhang above the limit that no fin covers
- **THEN** `overhang_exceeded` is still emitted for the part union
