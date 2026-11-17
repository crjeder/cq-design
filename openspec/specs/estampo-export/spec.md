# estampo-export Specification

## Purpose

Define the `estampo.toml` deliverable written by `build.py --formats estampo`: a slicer config for the delivered STLs, generated from the plan and `profile.json`.

## Requirements

### Requirement: estampo.toml is generated from the plan and profile

When the `estampo` format is requested, the exporter SHALL write `estampo.toml` into the output directory. It SHALL contain one `[[parts]]` entry per STL written for the model (a per-union STL, or a `plate_<n>.stl` for a plate holding several unions), with `file` set to that STL's file name and `rotate = [0, 0, 0]`, since the STLs are already in print pose and estampo's default `orient = "flat"` would otherwise re-orient them. Copies of a part already have their own STL, so `copies` is left at its default. The file SHALL be plain TOML text; generating it SHALL NOT require estampo to be installed.

#### Scenario: Single-union model

- **WHEN** a plan with one union `body` is built with `--formats estampo`
- **THEN** `out/estampo.toml` has exactly one `[[parts]]` entry with `file = "body.stl"` and the STL is present in `out/`

#### Scenario: Print-in-place plate

- **WHEN** two unions share a plate and the model is built with `--formats estampo`
- **THEN** the TOML has one `[[parts]]` entry for `plate_<n>.stl` and none for the two member unions

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

### Requirement: Staleness follows the other deliverables

`estampo.toml` SHALL be regenerated on every `build.py` run that requests it and SHALL always reference STL files written in that same run.

#### Scenario: STL not requested explicitly

- **WHEN** `build.py --formats estampo` runs
- **THEN** the STLs referenced by `estampo.toml` are also written to the output directory

### Requirement: Parts carrying fin unions disable slicer supports
When a part's plan contains a `sacrificial: true` fin union, the estampo export SHALL
write `enable_support = false` for that part, because the support is designed into the
STL.

#### Scenario: Fins present
- **WHEN** a part has a sacrificial fin union
- **THEN** its estampo entry has `enable_support = false`

#### Scenario: No fins
- **WHEN** a part has no sacrificial union
- **THEN** the existing `enable_support` derivation is unchanged
