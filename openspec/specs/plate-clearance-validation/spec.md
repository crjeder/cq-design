# plate-clearance-validation Specification

## Purpose

Define how the quality gate verifies that unions sharing a plate (print-in-place) keep a
minimum surface gap above one layer height, so the slicer does not bridge the gap and fuse
them into a single solid. The check runs entirely in-process (trimesh + python-fcl, no
slicer or MCP), measures on the assembled-pose per-union meshes the kinematic check already
consumes, and reports findings using the shared quality gate issue contract.

## Requirements

### Requirement: The gate checks clearance between co-plated unions

The quality gate SHALL, for every plate that holds more than one union, compute the
minimum surface-to-surface distance between each unordered pair of unions sharing that
plate, and SHALL flag any pair whose gap is at or below the plate clearance threshold.
Plate membership SHALL be derived the same way the model exporter derives it (a part's
explicit `plate`, otherwise the part's own `id`), so the gate and the exporter agree on
which unions are co-plated. Plates holding a single union SHALL be skipped.

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

### Requirement: Clearance is measured on the assembled-pose union meshes

The clearance check SHALL measure distances on the assembled-pose per-union meshes already
produced for the kinematic check, relying on the fact that a plate is fused as a rigid
cluster whose shared print-orientation rotation preserves pairwise distances. The check
SHALL NOT require print-orientation to have run and SHALL NOT introduce a new export
artifact.

#### Scenario: Assembled-pose gap equals print-orientation gap
- **WHEN** a plate's unions are rotated together into print orientation by the exporter
- **THEN** the minimum gap measured between two of those unions in the assembled pose
  equals the gap in the print orientation, so the assembled-pose measurement is valid

#### Scenario: Reuses the kinematic-stage meshes
- **WHEN** the gate runs the plate-clearance stage
- **THEN** it consumes the same assembled-pose per-union STLs handed to the kinematic
  stage and does not trigger an additional export

### Requirement: The clearance threshold is one layer height

The plate clearance threshold SHALL be one layer height, derived from the plan's
`nozzle_mm` the same way the gate derives `layer_height_mm` for its print recipe
(`nozzle_mm * 0.5`). A pair SHALL pass only when its minimum gap is strictly greater than
this threshold; a gap at or below it SHALL be flagged.

#### Scenario: Threshold matches the recipe layer height
- **WHEN** the gate computes the plate clearance threshold for a plan with a given
  `nozzle_mm`
- **THEN** the threshold equals the `layer_height_mm` the gate reports in its print recipe
  for the same plan

#### Scenario: Gap exactly at threshold is flagged
- **WHEN** two co-plated unions are separated by exactly one layer height
- **THEN** the pair is flagged (the comparison is at-or-below, not strictly below)

### Requirement: Plate-clearance findings use the structured issue contract and block a clean pass

Plate-clearance findings SHALL be emitted as issue objects matching the quality gate
contract: each issue SHALL have `source: "geometry"`, a `severity`, a `type`, a
human-readable `message`, and a `hint`. Flagged pairs SHALL use `type: "plate_clearance"`
with `severity: "error"`, and SHALL additionally carry the offending `plate`, the two
union ids, the measured `gap_mm`, and the `threshold_mm`. Because fusing is a hard print
failure, a `plate_clearance` error SHALL block a clean pass.

#### Scenario: Issue shape
- **WHEN** a plate-clearance issue is emitted
- **THEN** it contains `source`, `severity`, `type`, `message`, and `hint` keys and is
  consumable by the fix-prompt renderer without modification

#### Scenario: Error blocks a clean pass
- **WHEN** a `plate_clearance` issue is emitted
- **THEN** the gate does not report a clean pass and the issue surfaces in the fix prompt

### Requirement: Missing geometry dependencies degrade to a warning

The clearance stage SHALL degrade to a warning when the geometry dependencies it needs
(trimesh and its collision/distance backend) cannot be imported: it SHALL emit a single
issue with `severity: "warning"` and `type: "check_skipped"` and SHALL NOT raise, matching
the kinematic check's degrade behavior.

#### Scenario: Backend unavailable
- **WHEN** trimesh or the distance backend cannot be imported and a plate holds more than
  one union
- **THEN** the stage emits one `check_skipped` warning and performs no comparison, without
  raising
