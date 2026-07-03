## ADDED Requirements

### Requirement: Placement and orientation transforms do not serialize the shape

The placement helper `placement.apply_cq` SHALL apply rotations and translations
directly through the OCCT kernel (`BRepBuilderAPI_Transform` on the shape's underlying
`TopoDS_Shape`, with the kernel copy flag), and SHALL NOT route the transform through any
operation that pickles or `copy.deepcopy`s the shape. This helper positions a union into
the assembled frame and applies its recommended print orientation for the model export.
The behavior SHALL hold regardless of whether `cq_warehouse.extensions` has monkeypatched
`Shape._apply_transform`/`Shape.copy`, so transforms never trigger a `BinTools`
serialization round-trip. The composed transform SHALL preserve the existing `placement`
convention: rotations are applied in listed order about axes through the origin, then the
translation, and an absent or empty placement is the identity.

#### Scenario: Transform of patch-affected geometry does not deep-copy

- **WHEN** `cq_warehouse.extensions` is imported (its global `Shape` patch active) and a
  union's geometry is transformed by `apply_cq` for placement or print orientation
- **THEN** the transform is applied without entering the patched `Shape.copy` /
  `copy.deepcopy`, no `BinTools` write/read round-trip occurs, and the export does not
  raise `BinTools_ShapeSet::ReadGeometry` / `BRep_PointRepresentation` errors

#### Scenario: Transform result matches the placement convention

- **WHEN** a placement with one or more `rotate` steps and a `translate_mm` is applied
  via `apply_cq`
- **THEN** the resulting pose is identical to the same placement composed by
  `placement.to_matrix` (rotations in listed order about the origin, then translation)

#### Scenario: Identity placement is unchanged

- **WHEN** `apply_cq` is called with an absent or empty placement
- **THEN** the workplane is returned unchanged, with no transform applied
