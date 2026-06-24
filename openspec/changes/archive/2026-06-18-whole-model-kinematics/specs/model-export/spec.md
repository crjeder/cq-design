## ADDED Requirements

### Requirement: Unions export as separately named objects in an assembled 3MF

The exporter SHALL produce a 3MF in which each union is a separately named object
carrying its assembled-pose transform, so a printer operator can re-distribute
objects across plates. Each object SHALL carry its `plate` tag as metadata. The
exporter SHALL NOT boolean-fuse distinct unions in the 3MF. This assembled 3MF
SHALL be the source of truth for the per-union meshes consumed by the kinematic
check.

#### Scenario: Each union is a named 3MF object in assembled pose
- **WHEN** a model with multiple unions is exported to 3MF
- **THEN** each union appears as a separately named object positioned in its
  assembled pose, with its plate recorded as metadata, and no two unions are fused

#### Scenario: Print-in-place unions form a locked cluster
- **WHEN** several unions share one plate (print-in-place)
- **THEN** they are exported as a locked cluster whose relative transforms are
  fixed, so the operator can move the cluster but not separate its members

---

### Requirement: STL export is a single-body fallback

For STL consumers, the exporter SHALL emit one STL per union (for checking and
single-object use) and, for any plate holding more than one union, one fused STL
per plate (because STL cannot carry multiple objects in fixed relative pose).

#### Scenario: Per-union STL plus fused plate STL
- **WHEN** a plate holds two print-in-place unions and STL output is requested
- **THEN** the exporter emits one STL per union and one fused STL for the plate
