## ADDED Requirements

### Requirement: fold_metrics measures adjacent-face folds
`mesh_io.fold_metrics(mesh, min_interior_deg)` SHALL compute, for every pair of triangles sharing an edge, the interior dihedral angle (180 degrees minus the angle between their normals), and SHALL return the number of fold clusters below `min_interior_deg`, the sharpest interior angle, its location, and the smallest face area among the folded faces. It SHALL NOT require CadQuery.

#### Scenario: Zero-thickness fin
- **WHEN** two adjacent triangles have opposite normals (interior angle near 0 degrees)
- **THEN** `fold_metrics` reports one cluster with the sharpest angle near 0 and the location of that edge

#### Scenario: Ordinary corners and curves
- **WHEN** the mesh is a box, a cylinder, or a filleted plate (adjacent normals differ by at most 90 degrees)
- **THEN** `fold_metrics` reports zero clusters

#### Scenario: One fin reports once
- **WHEN** a fin is made of many adjacent triangle pairs along one seam
- **THEN** they are reported as a single cluster, not one per pair

### Requirement: The gate reports fins as an advisory finding
`quality_gate._analyze_stl` SHALL emit one `sliver_fin` issue, using the shared `{source, severity, type, message, hint, ...}` contract with `severity: "warning"`, when `fold_metrics` finds any fold with an interior angle below 10 degrees. The issue SHALL carry the cluster count, the sharpest interior angle in degrees, and the location in the build frame of up to the five sharpest clusters. It SHALL NOT fail the gate on its own.

#### Scenario: Tangent prism fillet running past a tapered, chamfered rib
- **WHEN** a part unions a spandrel prism fillet along a rib that tapers and has a bottom chamfer, and the prism continues past the point where the rib flank is as deep as the fillet
- **THEN** the gate emits a `sliver_fin` warning listing the fin locations and their interior angles

#### Scenario: Clean part
- **WHEN** no adjacent triangle pair has an interior angle below 10 degrees
- **THEN** no `sliver_fin` issue is emitted and the gate output is unchanged

#### Scenario: Tapered rib tip is not a fin
- **WHEN** a part has a deliberate wedge tip of about 20 degrees
- **THEN** no `sliver_fin` issue is emitted for it

#### Scenario: Location uses the build frame
- **WHEN** the part's print orientation rotates the part
- **THEN** the reported locations are in the rotated (build) frame, matching `overhang_exceeded`

### Requirement: The finding hint names the cause and the fix
The `sliver_fin` hint SHALL state that the fin is typically a tangent (spandrel or prism) fillet whose razor-thin tip runs past the wall it sits on, or solids ending flush, and SHALL point to ending the fillet where the wall is deeper than the fillet plus any chamfer, or using `.edges(...).fillet()` on the selected edge.

#### Scenario: Hint content
- **WHEN** a `sliver_fin` issue is emitted
- **THEN** its `hint` mentions ending the fillet on the wall and native `.fillet()`
