## MODIFIED Requirements

### Requirement: Unions export as separately named objects in an assembled 3MF

The exporter SHALL produce a 3MF in which each union is a separately named object
carrying its assembled-pose transform, so a printer operator can re-distribute
objects across plates. Each object's name SHALL be derived from the part's
`description` in the build plan, sanitized into a valid, readable label (internal
whitespace collapsed, control characters removed, length bounded); when the
sanitized description is empty the exporter SHALL fall back to the part `id`. Each
object SHALL carry its `plate` tag as metadata. The exporter SHALL NOT boolean-fuse
distinct unions in the 3MF. This assembled 3MF SHALL be the source of truth for the
per-union meshes consumed by the kinematic check.

#### Scenario: Each union is a named 3MF object in assembled pose
- **WHEN** a model with multiple unions is exported to 3MF
- **THEN** each union appears as a separately named object positioned in its
  assembled pose, with its plate recorded as metadata, and no two unions are fused

#### Scenario: Object name reflects the part description
- **WHEN** a part with `description` "Hinged lid that snaps onto the base" is exported
- **THEN** the corresponding 3MF object's `name` attribute is the sanitized
  description, not the part `id` or a kernel-generated placeholder such as
  "CadQuery Shape 0"

#### Scenario: Description with hostile or oversized content is sanitized
- **WHEN** a part description contains newlines, control characters, or exceeds the
  name length cap
- **THEN** the exporter writes a single-line, control-character-free, length-bounded
  object name and the 3MF remains valid XML

#### Scenario: Print-in-place unions form a locked cluster
- **WHEN** several unions share one plate (print-in-place)
- **THEN** they are exported as a locked cluster whose relative transforms are
  fixed, so the operator can move the cluster but not separate its members
