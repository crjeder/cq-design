## ADDED Requirements

### Requirement: Mesh helper loops are vectorized without changing results
`measure_stl._union_find`, `measure_stl._flat_faces` and `print_orientation._area_cumulation_normals` SHALL be computed with numpy/scipy array operations rather than per-face or per-edge Python loops.

#### Scenario: Results unchanged
- **WHEN** any of the three helpers runs on any mesh
- **THEN** the components, flat-face groups and candidate normals (including order) are identical to those produced before the change

#### Scenario: Dense mesh
- **WHEN** the mesh has tens of thousands of faces
- **THEN** no helper does per-face or per-edge arithmetic in Python; remaining loops only skip already-grouped faces or iterate groups and buckets
