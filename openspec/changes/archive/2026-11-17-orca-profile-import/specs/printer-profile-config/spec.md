## ADDED Requirements

### Requirement: Optional orca block

The profile schema SHALL accept an optional `orca` object with `app` (one of
`OrcaSlicer`, `Snapmaker_Orca`, `BambuStudio`), `data_dir`, `machine`, `process`,
`process_purpose` (one of `visual`, `functional`, `draft`, `user`), `filaments` (non-empty
array of strings), `processes` (non-empty array of `{name, layer_height_mm, wall_loops,
infill_density, user}`) and `digest` (string), all required when the block is present, with
`additionalProperties: false`. Only `orca_profile.py` and the planner (via `processes`)
SHALL read it; other consumers read the plain profile fields.

#### Scenario: Valid orca block
- **WHEN** `profile.json` carries a complete `orca` block
- **THEN** validation passes

#### Scenario: Incomplete orca block
- **WHEN** the `orca` block omits `digest`
- **THEN** validation fails naming `digest`

### Requirement: Optional build volume

The profile schema SHALL accept an optional `build_volume_mm` object with positive
numbers `x`, `y`, `z`, all required when present.

#### Scenario: Valid build volume
- **WHEN** `profile.json` declares `"build_volume_mm": {"x": 270, "y": 270, "z": 270}`
- **THEN** validation passes

## MODIFIED Requirements

### Requirement: Seed the profile on first use in a directory

The system SHALL seed `profile.json` into the working directory by copying
`src/profile.default.json` verbatim when no `profile.json` already exists
there. An existing `profile.json` SHALL NOT be overwritten or merged. The seeding
step SHALL run once per directory, before Phase 1, alongside the existing permission
bootstrap. When the profile was seeded in this run and an Orca-family install is found,
the seeded profile SHALL then be filled by the `orca-profile-import` capability.

#### Scenario: First run in a fresh directory

- **WHEN** the skill runs in a directory with no `profile.json`
- **THEN** the skill copies `src/profile.default.json` to `./profile.json`
- **AND** informs the user that a default profile was seeded and where to edit it

#### Scenario: First run with Orca installed

- **WHEN** the skill seeds `profile.json` and an Orca-family install is found
- **THEN** the seeded profile is filled from the Orca presets and the user is shown the
  imported values and the process selection reason

#### Scenario: Subsequent run leaves an edited profile untouched

- **WHEN** the skill runs in a directory where `profile.json` already exists
- **THEN** the skill does not modify, overwrite, re-seed, or import into the file
