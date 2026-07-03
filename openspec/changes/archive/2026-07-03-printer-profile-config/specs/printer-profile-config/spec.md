## ADDED Requirements

### Requirement: Repo-root printer profile file

The system SHALL support an optional `printer_profile.json` file in the working directory
(the same directory as `BUILD_PLAN.json`) that records a user's default `printer`,
`material`, `nozzle_mm`, and `constraints` (`wall_min_mm`, `overhang_max_deg`,
`dimension_tolerance_mm`). The file's shape SHALL be validated against
`src/printer_profile_schema.json`, a JSON Schema draft-7 document mirroring the equivalent
subset of `build_plan_schema.json`.

#### Scenario: Valid profile

- **WHEN** `printer_profile.json` in the working directory declares `printer`, `material`,
  `nozzle_mm`, and `constraints` matching the schema
- **THEN** validation passes and the profile's values are available to the planning phase

#### Scenario: Missing required field

- **WHEN** `printer_profile.json` exists but omits `nozzle_mm`
- **THEN** validation fails, naming the missing field, and the planning phase falls back to
  asking the user for that field as if no profile existed

### Requirement: Default profile shipped with the skill

The skill SHALL ship a default profile template at `src/printer_profile.default.json`,
containing values that validate against `src/printer_profile_schema.json` and matching the
constraint defaults already used as examples in `prompts/planning.md`
(`wall_min_mm: 1.2`, `overhang_max_deg: 45`, `dimension_tolerance_mm: 0.5`).

#### Scenario: Default template is valid

- **WHEN** `src/printer_profile.default.json` is validated against
  `src/printer_profile_schema.json`
- **THEN** validation passes

### Requirement: Seed the profile on first use in a directory

The system SHALL seed `printer_profile.json` into the working directory by copying
`src/printer_profile.default.json` verbatim when no `printer_profile.json` already exists
there. An existing `printer_profile.json` SHALL NOT be overwritten or merged. The seeding
step SHALL run once per directory, before Phase 1, alongside the existing permission
bootstrap.

#### Scenario: First run in a fresh directory

- **WHEN** the skill runs in a directory with no `printer_profile.json`
- **THEN** the skill copies `src/printer_profile.default.json` to
  `./printer_profile.json`
- **AND** informs the user that a default profile was seeded and where to edit it

#### Scenario: Subsequent run leaves an edited profile untouched

- **WHEN** the skill runs in a directory where `printer_profile.json` already exists
- **THEN** the skill does not modify, overwrite, or re-seed the file

### Requirement: Per-model overrides persist to the profile as the new project default

When the user explicitly states a `printer`, `material`, `nozzle_mm`, or `constraints` value
for the current model that differs from `printer_profile.json`, and does not indicate the
value is a one-time exception, the system SHALL write only the stated field(s) back into
`printer_profile.json` in the working directory, leaving unmentioned fields unchanged, and
SHALL re-validate the file against `src/printer_profile_schema.json` after writing. The system
SHALL announce the update to the user in the same turn. When the user indicates the value is a
one-time exception, the system SHALL use it for the current model only and SHALL NOT write it
back.

#### Scenario: Stated override updates only the mentioned field

- **WHEN** the user states a different `nozzle_mm` for the current model without indicating a
  one-time exception, and `printer_profile.json` already declares `printer`, `material`, and
  `constraints`
- **THEN** `printer_profile.json` is rewritten with the new `nozzle_mm` value
- **AND** `printer`, `material`, and `constraints` in the file are unchanged
- **AND** the user is told the project default was updated

#### Scenario: One-time exception does not persist

- **WHEN** the user states a different `printer` for the current model and explicitly says
  it's a one-off, not a new default
- **THEN** `printer_profile.json` on disk is left unchanged
