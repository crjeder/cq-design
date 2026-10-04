## MODIFIED Requirements

### Requirement: Repo-root printer profile file

The system SHALL support an optional `profile.json` file in the working directory
(the same directory as `BUILD_PLAN.json`) that records a user's default `printer`,
`material`, `nozzle_mm`, and `constraints` (`wall_min_mm`, `overhang_max_deg`,
`dimension_tolerance_mm`). The file's shape SHALL be validated against
`src/printer_profile_schema.json`, a JSON Schema draft-7 document mirroring the equivalent
subset of `build_plan_schema.json`.

#### Scenario: Valid profile

- **WHEN** `profile.json` in the working directory declares `printer`, `material`,
  `nozzle_mm`, and `constraints` matching the schema
- **THEN** validation passes and the profile's values are available to the planning phase

#### Scenario: Missing required field

- **WHEN** `profile.json` exists but omits `nozzle_mm`
- **THEN** validation fails, naming the missing field, and the planning phase falls back to
  asking the user for that field as if no profile existed

### Requirement: Default profile shipped with the skill

The skill SHALL ship a default profile template at `src/profile.default.json`,
containing values that validate against `src/printer_profile_schema.json` and matching the
constraint defaults already used as examples in `prompts/planning.md`
(`wall_min_mm: 1.2`, `overhang_max_deg: 45`, `dimension_tolerance_mm: 0.5`). The template
SHALL include a `slicer` block with a valid `preferred_format`.

#### Scenario: Default template is valid

- **WHEN** `src/profile.default.json` is validated against
  `src/printer_profile_schema.json`
- **THEN** validation passes

### Requirement: Seed the profile on first use in a directory

The system SHALL seed `profile.json` into the working directory by copying
`src/profile.default.json` verbatim when no `profile.json` already exists
there. An existing `profile.json` SHALL NOT be overwritten or merged. The seeding
step SHALL run once per directory, before Phase 1, alongside the existing permission
bootstrap.

#### Scenario: First run in a fresh directory

- **WHEN** the skill runs in a directory with no `profile.json`
- **THEN** the skill copies `src/profile.default.json` to `./profile.json`
- **AND** informs the user that a default profile was seeded and where to edit it

#### Scenario: Subsequent run leaves an edited profile untouched

- **WHEN** the skill runs in a directory where `profile.json` already exists
- **THEN** the skill does not modify, overwrite, or re-seed the file

## ADDED Requirements

### Requirement: Optional slicer block

The profile schema SHALL accept an optional `slicer` object with `preferred_format` (string,
one of `3mf`, `stl`, `step`, `obj`, `iges`, `scad`) and `slicer_name` (non-empty string, free
text, informational only). When the `slicer` object is present, `preferred_format` SHALL be
required. `additionalProperties` SHALL be `false` on the block.

#### Scenario: Valid slicer block

- **WHEN** `profile.json` declares `"slicer": {"preferred_format": "3mf", "slicer_name": "OrcaSlicer"}`
- **THEN** validation passes

#### Scenario: Unknown format

- **WHEN** `slicer.preferred_format` is `"gcode"`
- **THEN** validation fails at `slicer -> preferred_format`

#### Scenario: Slicer block without a format

- **WHEN** `slicer` is present with only `slicer_name`
- **THEN** validation fails naming `preferred_format`

### Requirement: build.py requires a preferred output format

`build.py` SHALL read `profile.json` from the project root (next to `BUILD_PLAN.json`) and
SHALL write the `slicer.preferred_format` deliverable for every union in addition to the
always-written `model.3mf` and STL outputs. When `profile.json` is missing, invalid, or has no
`slicer.preferred_format`, `build.py` SHALL exit 1 before exporting, with a message naming the
missing setting. `--formats` SHALL remain additive. `3mf` and `stl` as preferred formats SHALL
add no extra files.

#### Scenario: Preferred format configured

- **WHEN** `slicer.preferred_format` is `"step"` and `build.py` runs without `--formats`
- **THEN** `<union-id>.step` is written per union alongside `model.3mf` and the STLs

#### Scenario: Preferred format missing

- **WHEN** `profile.json` has no `slicer` block
- **THEN** `build.py` exits 1 with an error naming `slicer.preferred_format` and writes no outputs

#### Scenario: Profile file missing

- **WHEN** no `profile.json` exists in the project root
- **THEN** `build.py` exits 1 with an error naming `profile.json`

#### Scenario: Extra formats combine

- **WHEN** `preferred_format` is `"step"` and `--formats obj` is passed
- **THEN** both `step` and `obj` files are written per union
