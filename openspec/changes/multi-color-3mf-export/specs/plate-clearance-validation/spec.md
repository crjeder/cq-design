## MODIFIED Requirements

### Requirement: The gate checks clearance between co-plated unions

The quality gate SHALL, for every plate that holds more than one union, compute the
minimum surface-to-surface distance between each unordered pair of unions sharing that
plate, and SHALL flag any pair whose gap is at or below the plate clearance threshold.
Plate membership SHALL be derived the same way the model exporter derives it (a part's
explicit `plate`, otherwise the part's own `id`), so the gate and the exporter agree on
which unions are co-plated. Plates holding a single union SHALL be skipped. A pair whose
two unions declare the same `object` SHALL be exempt from the clearance threshold (its
members touch by design) and SHALL instead be checked for overlap.

#### Scenario: Pair below threshold is flagged
- **WHEN** two unions share a plate and their minimum surface-to-surface gap is at or
  below the clearance threshold
- **THEN** the gate emits a `plate_clearance` issue naming both unions and the plate

#### Scenario: Pair above threshold passes
- **WHEN** every pair of unions sharing a plate has a minimum gap strictly greater than
  the clearance threshold
- **THEN** the gate emits no plate-clearance issue for that plate

#### Scenario: Single-union plate is skipped
- **WHEN** a plate holds exactly one union
- **THEN** the gate performs no clearance comparison for that plate and emits no
  plate-clearance issue for it

#### Scenario: All unions on their own plates
- **WHEN** no plate holds more than one union
- **THEN** the plate-clearance stage performs no comparison and contributes no issues

#### Scenario: Touching members of one object pass
- **WHEN** two co-plated unions share an `object` and touch with zero gap but no overlap
  volume
- **THEN** the gate emits no `plate_clearance` issue for that pair

## ADDED Requirements

### Requirement: Members of one object must be disjoint

For each pair of co-plated unions that share an `object`, the gate SHALL measure the
intersection volume of their assembled-pose meshes and SHALL emit an issue with
`source: "geometry"`, `severity: "error"`, `type: "object_member_overlap"`, the `object`
id, both union ids and the measured `overlap_mm3` when that volume exceeds 0.1 mm^3
(the kinematic check's default penetration tolerance). The issue SHALL block a clean pass.

#### Scenario: Overlapping members are flagged
- **WHEN** two members of one `object` interpenetrate by more than the tolerance
- **THEN** the gate emits one `object_member_overlap` error naming the object, both
  unions and the overlap volume, and does not report a clean pass

#### Scenario: Disjoint members pass
- **WHEN** two members of one `object` share only a boundary surface
- **THEN** the gate emits no `object_member_overlap` issue
