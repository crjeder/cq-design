## MODIFIED Requirements

### Requirement: Unions export as separately named objects in an assembled 3MF

The exporter SHALL produce a 3MF in which each union is a separately named object. Each
object's geometry SHALL be written in the union's **recommended print orientation** when
one is supplied, so the deliverable is ready to print; when no print orientation is
supplied the object SHALL be written in its assembled-pose transform as before. Each
object's name SHALL be derived from the part's `description` in the build plan, sanitized
into a valid, readable label (internal whitespace collapsed, control characters removed,
length bounded); when the sanitized description is empty the exporter SHALL fall back to
the part `id`. Each object SHALL carry its `plate` tag as metadata. The exporter SHALL NOT
boolean-fuse distinct unions in the 3MF.

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

#### Scenario: Description with hostile or oversized content is sanitized
- **WHEN** a part description contains newlines, control characters, or exceeds the name
  length cap
- **THEN** the exporter writes a single-line, control-character-free, length-bounded object
  name and the 3MF remains valid XML

#### Scenario: Print-in-place unions form a locked cluster
- **WHEN** several unions share one plate (print-in-place)
- **THEN** they are exported as a locked cluster whose relative transforms are fixed, so
  the operator can move the cluster but not separate its members

## ADDED Requirements

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
