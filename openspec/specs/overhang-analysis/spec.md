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

A steeply down-facing face whose centroid sits within a first-layer-height band of the
mesh's lowest point is resting on the print bed; the bed supports it, not support
material, so the analysis SHALL exclude it from overhang classification. In particular a
part's flat bottom face (a 90-degree downward face at the lowest level) SHALL NOT be
reported as an overhang. A downward face that sits above that band (for example the
underside of an elevated ledge or internal ceiling) SHALL remain subject to overhang
classification.

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
