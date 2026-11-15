## MODIFIED Requirements

### Requirement: Slicer overrides come from profile and plan data

The generated file SHALL write `[slicer.<engine>.overrides]` only with values that exist in `profile.json` or the plan: layer height, infill density, and wall loops. Wall loops SHALL be `ceil(wall_min_mm / line_width_mm)` using the plan's `constraints.wall_min_mm` and `motion.line_width_mm`, and SHALL be omitted when either is absent. Support and brim SHALL be emitted per `[[parts]]` entry as `enable_support` and `brim_type` from the print-pose mesh, never as global overrides. A value that is absent SHALL be omitted, never defaulted. Printer, process and filament profile names SHALL be written only when `profile.json` `slicer.estampo` supplies them; otherwise they SHALL appear as commented placeholders.

#### Scenario: Profile values mapped

- **WHEN** `profile.json` has `layer_height_mm` 0.2 and `infill_density` 0.15
- **THEN** the overrides table contains `layer_height = 0.2` and `sparse_infill_density = "15%"` for the orca engine

#### Scenario: Wall loops from minimum wall

- **WHEN** `wall_min_mm` is 1.2 and `line_width_mm` is 0.45
- **THEN** the overrides table contains `wall_loops = 3`

#### Scenario: Exact multiple does not add a loop

- **WHEN** `wall_min_mm` is 0.9 and `line_width_mm` is 0.45
- **THEN** the overrides table contains `wall_loops = 2`

#### Scenario: Line width absent

- **WHEN** `profile.json` has no `motion.line_width_mm`
- **THEN** no `wall_loops` key is written

#### Scenario: Per-part support and brim

- **WHEN** a part's print-pose STL has non-bridge overhang area and little bed contact
- **THEN** its `[[parts]]` entry has `enable_support = true` and `brim_type = "brim"`

#### Scenario: No printer profile name supplied

- **WHEN** `profile.json` has no `slicer.estampo` block
- **THEN** the file contains no uncommented `printer`, `process` or `filaments` key and says so in a comment
