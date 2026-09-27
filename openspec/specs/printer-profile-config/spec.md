# Printer Profile Config

## Purpose

Defines the repo-root `printer_profile.json` file that records a user's default printer,
material, nozzle, and constraint settings, the schema it must conform to, how it is seeded
into a new working directory, and how per-model overrides persist back to it as the new
project default.

## Requirements

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

### Requirement: Optional bridge length limit
`printer_profile.json` SHALL accept an optional `constraints.bridge_max_mm` (number, minimum 0). When absent, consumers SHALL use 10.0.

#### Scenario: Existing profile still validates
- **WHEN** a profile without `bridge_max_mm` is validated
- **THEN** validation succeeds

#### Scenario: Negative value rejected
- **WHEN** `bridge_max_mm` is -1
- **THEN** validation fails

### Requirement: Optional motion block for toolhead speed modeling

`printer_profile.json` SHALL accept an optional top-level `motion` object carrying
`v_cruise_mm_s`, `accel_mm_s2`, `junction_deviation_mm`, `min_layer_time_s`,
`layer_height_mm`, `line_width_mm`, and `infill_density` (all positive numbers). The
file's shape SHALL be validated against the updated `src/printer_profile_schema.json`.
When `motion` is absent, consumers that need it (the toolpath-speed-advisor capability)
SHALL treat this as a stated skip and SHALL NOT assume default values for any of its
fields. Existing profiles without a `motion` block SHALL continue to validate.

#### Scenario: Profile with a valid motion block validates

- **WHEN** `printer_profile.json` declares a `motion` object with all seven fields as
  positive numbers
- **THEN** validation passes and the values are available to consumers that use them

#### Scenario: Profile without a motion block still validates

- **WHEN** `printer_profile.json` omits `motion` entirely
- **THEN** validation passes, exactly as before this capability existed

#### Scenario: Partial motion block is rejected, not defaulted

- **WHEN** `printer_profile.json` declares a `motion` object missing one of the seven
  required fields
- **THEN** validation fails, naming the missing field, rather than silently defaulting it

#### Scenario: Per-model override persists into the motion block

- **WHEN** the user explicitly states a different `motion.accel_mm_s2` for the current
  model without indicating a one-time exception
- **THEN** `printer_profile.json` is rewritten with the new value under `motion`, other
  `motion` fields and top-level fields are unchanged, and the file re-validates

### Requirement: Optional top/bottom shell layer count

`printer_profile.json` SHALL accept an optional `constraints.top_bottom_layers` (integer,
minimum 1). When absent, consumers SHALL use 4, matching the value already assumed before
this capability existed.

#### Scenario: Existing profile without the field still validates
- **WHEN** a profile without `constraints.top_bottom_layers` is validated
- **THEN** validation succeeds

#### Scenario: Declared value is used by print-recipe generation
- **WHEN** a profile declares `constraints.top_bottom_layers: 6`
- **THEN** `quality_gate.py`'s generated print recipe uses `6`, not the previous hardcoded
  default of `4`

#### Scenario: Value below the minimum is rejected
- **WHEN** `constraints.top_bottom_layers` is `0`
- **THEN** validation fails, naming the field, rather than silently clamping it

### Requirement: Declared `motion.layer_height_mm` is authoritative for print-recipe generation

When `printer_profile.json` declares a `motion` block, the system SHALL use its
`layer_height_mm` as the print recipe's `layer_height_mm` instead of deriving it from
`nozzle_mm`. When no `motion` block is declared, consumers SHALL continue to derive
`layer_height_mm` as `nozzle_mm * 0.5`, exactly as before this capability existed.

#### Scenario: Motion block's layer height overrides the nozzle-derived default
- **WHEN** a profile declares `motion.layer_height_mm: 0.16` with `nozzle_mm: 0.4`
- **THEN** the generated print recipe's `layer_height_mm` is `0.16`, not `0.2`

#### Scenario: No motion block keeps the existing derivation
- **WHEN** a profile declares no `motion` block
- **THEN** the generated print recipe's `layer_height_mm` is `nozzle_mm * 0.5`, exactly as
  before this capability existed
