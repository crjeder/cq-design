## ADDED Requirements

### Requirement: Overhang region analysis does not re-access mesh properties per region
`overhang_regions` SHALL read the mesh vertex, face and face-area arrays once per call and reuse them for every region, so analysis time does not scale with region count times mesh size through trimesh cache verification.

#### Scenario: Results unchanged
- **WHEN** `overhang_regions`, `overhang_metrics` or `support_cost` runs on any mesh
- **THEN** the regions, bridge flags, areas and costs are identical to those produced before the change

#### Scenario: Many small regions
- **WHEN** a mesh produces thousands of overhang regions
- **THEN** `mesh.vertices`, `mesh.faces` and `mesh.area_faces` are each accessed a constant number of times per call, independent of region count
