# model-export Specification

## Purpose

Define how a whole model of unions and plates is exported: an assembled 3MF whose
unions are separately named objects (the source of truth for kinematic-check
meshes), and a single-body STL fallback emitted per union and per multi-union plate.

## Requirements

### Requirement: Unions export as separately named objects in an assembled 3MF

The exporter SHALL produce a 3MF in which each union is a separately named object. Each
object's geometry SHALL be written in the union's **recommended print orientation** when
one is supplied, so the deliverable is ready to print; when no print orientation is
supplied the object SHALL be written in its assembled-pose transform as before. Each
object's name SHALL be derived from the part's `description` in the build plan, sanitized
into a valid, readable label (internal whitespace collapsed, control characters removed,
length bounded); when the sanitized description is empty the exporter SHALL fall back to
the part `id`. Object names SHALL be unique across the 3MF: when two or more parts would
otherwise produce the same name, the exporter SHALL disambiguate each colliding object by
suffixing its name with the part `id` (which is unique), and SHALL leave non-colliding
names unchanged. Each object SHALL carry its `plate` tag as metadata. The exporter SHALL
NOT boolean-fuse distinct unions in the 3MF.

#### Scenario: Each union is a named 3MF object
- **WHEN** a model with multiple unions is exported to 3MF
- **THEN** each union appears as a separately named object, with its plate recorded as
  metadata, and no two unions are fused

#### Scenario: Deliverable is written in the recommended print orientation
- **WHEN** a union has a recommended print orientation and the model is exported to 3MF
- **THEN** that object's geometry is written in the print orientation (not the assembled
  pose), ready for the printer

#### Scenario: Falls back to assembled pose when no print orientation is given
- **WHEN** a union has no recommended print orientation
- **THEN** the object is written in its assembled-pose transform

#### Scenario: Object name reflects the part description
- **WHEN** a part with `description` "Hinged lid that snaps onto the base" is exported
- **THEN** the corresponding 3MF object's `name` attribute is the sanitized description,
  not the part `id` or a kernel-generated placeholder such as "CadQuery Shape 0"

#### Scenario: Duplicate descriptions are disambiguated by part id
- **WHEN** two parts (e.g. ids "left_leaf" and "right_leaf") share the description
  "Hinge leaf"
- **THEN** the two 3MF objects get distinct names, each the description suffixed with its
  part id (e.g. "Hinge leaf (left_leaf)" and "Hinge leaf (right_leaf)"), so no two objects
  share a name

#### Scenario: Distinct descriptions are left unchanged
- **WHEN** every part's sanitized name is already unique across the model
- **THEN** each object keeps its plain sanitized description with no id suffix appended

#### Scenario: Description with hostile or oversized content is sanitized
- **WHEN** a part description contains newlines, control characters, or exceeds the name
  length cap
- **THEN** the exporter writes a single-line, control-character-free, length-bounded object
  name and the 3MF remains valid XML

#### Scenario: Print-in-place unions form a locked cluster
- **WHEN** several unions share one plate (print-in-place)
- **THEN** they are exported as a locked cluster whose relative transforms are fixed, so
  the operator can move the cluster but not separate its members

---

### Requirement: Assembled-pose meshes for the kinematic check are preserved

Independently of the print orientation applied to deliverables, the exporter SHALL still
produce one assembled-pose per-union mesh per union, in the union's `placement` pose, as
the source of truth consumed by the kinematic check. Applying a print orientation to the
deliverable SHALL NOT alter the assembled-pose meshes.

#### Scenario: Print orientation does not disturb the kinematic-check meshes
- **WHEN** unions are exported with recommended print orientations applied to the
  deliverable 3MF/STL
- **THEN** the per-union assembled-pose meshes consumed by the kinematic check are still
  written in each union's `placement` pose

---

### Requirement: STL export is a single-body fallback

For STL consumers, the exporter SHALL emit one STL per union (for checking and
single-object use) and, for any plate holding more than one union, one fused STL
per plate (because STL cannot carry multiple objects in fixed relative pose).

#### Scenario: Per-union STL plus fused plate STL
- **WHEN** a plate holds two print-in-place unions and STL output is requested
- **THEN** the exporter emits one STL per union and one fused STL for the plate

---

### Requirement: Placement and orientation transforms do not serialize the shape

The placement helper `placement.apply_cq` SHALL apply rotations and translations
directly through the OCCT kernel (`BRepBuilderAPI_Transform` on the shape's underlying
`TopoDS_Shape`, with the kernel copy flag), and SHALL NOT route the transform through any
operation that pickles or `copy.deepcopy`s the shape. This helper positions a union into
the assembled frame and applies its recommended print orientation for the model export.
The behavior SHALL hold regardless of whether `cq_warehouse.extensions` has monkeypatched
`Shape._apply_transform`/`Shape.copy`, so transforms never trigger a `BinTools`
serialization round-trip. The composed transform SHALL preserve the existing
`placement` convention: rotations are applied in listed order about axes through the
origin, then the translation, and an absent or empty placement is the identity.

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
