# Print Pose Finishing

## Purpose

Resolves orientation-dependent features (teardrop peak direction) from the accepted print pose: `print_up()` in part scripts, a pose-aware re-load at model export, a pose-stability guard, and pose provenance in the export manifest.

## Requirements

### Requirement: print_up reports print-up in the build pose
The `print_up()` helper SHALL return the print-up direction as a unit vector in the part's build pose, derived from `CQ_PRINT_ROTATE`, and SHALL return +Z when the variable is unset.

#### Scenario: Unset
- **WHEN** `CQ_PRINT_ROTATE` is not set
- **THEN** `print_up()` returns (0, 0, 1)

#### Scenario: Flipped pose
- **WHEN** `CQ_PRINT_ROTATE` is a 180 degree rotation about X
- **THEN** `print_up()` returns (0, 0, -1)

### Requirement: Teardrop blocks accept print_up
`teardrop_bore` and `teardrop_post` SHALL accept a `print_up` vector and orient their peak (bore) or flat (post) accordingly; `peak=` remains supported.

#### Scenario: Bore with flipped print-up
- **WHEN** `teardrop_bore(d, depth, print_up=(0, 0, -1))` is built
- **THEN** its apex lies at -Z

### Requirement: Finishing pass re-runs scripts with the accepted pose
After orientation is accepted and before model export, Phase 3 SHALL re-run each part script with `CQ_PRINT_ROTATE` set from `build/orientations.json`, without an LLM round.

#### Scenario: Pose available
- **WHEN** `build/orientations.json` has an entry for a part
- **THEN** the finishing run sets `CQ_PRINT_ROTATE` to that entry's `rotate` and the resulting geometry feeds export

#### Scenario: Authoring pass unchanged
- **WHEN** a script is run without `--print-rotate`
- **THEN** output is identical to the current behavior

### Requirement: Pose-stability guard
After the finishing pass the system SHALL re-score orientation and emit an advisory finding, keeping the accepted pose, if the newly chosen `rotate` differs.

#### Scenario: Pose shifts
- **WHEN** re-scoring picks a different `rotate` than the accepted one
- **THEN** an advisory finding names both poses and the accepted pose is kept

### Requirement: Finishing provenance
The export manifest SHALL record the `rotate` used in the finishing pass, and a mismatch with the current accepted orientation SHALL mark the export stale.

#### Scenario: Orientation re-accepted with a new pose
- **WHEN** `orientations.json` changes after export
- **THEN** freshness reports the export stale
