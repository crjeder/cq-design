## ADDED Requirements

### Requirement: Discover Orca-family slicer data

`src/orca_profile.py discover` SHALL list every Orca-family data dir (`OrcaSlicer`,
`Snapmaker_Orca`, `BambuStudio`) under the OS config root (Windows `%APPDATA%`, macOS
`~/Library/Application Support`, Linux `~/.config`) that contains a `system/` dir, with
the currently selected machine read from the app's `.conf` leading JSON object
(`presets.machine`) when present. `--data-dir` SHALL override discovery. No other slicer
family SHALL be discovered.

#### Scenario: One install found
- **WHEN** only `%APPDATA%/Snapmaker_Orca/system/` exists
- **THEN** `discover` returns one entry with app `Snapmaker_Orca` and its selected machine

#### Scenario: No install found
- **WHEN** no Orca-family dir exists
- **THEN** `discover` returns an empty list and exit code 0

#### Scenario: Several installs found
- **WHEN** both `OrcaSlicer` and `Snapmaker_Orca` dirs exist and `import` runs without
  `--data-dir`
- **THEN** `import` fails with a typed `ambiguous_data_dir` error listing both

### Requirement: Resolve preset inheritance

The tool SHALL resolve a machine, process or filament preset by name from `system/*/<kind>/`
and `user/*/<kind>/` (recursive), user presets shadowing system presets of the same name,
merging each child over its `inherits` parent until no parent remains. A missing parent or
an inheritance cycle SHALL be a typed error naming the chain resolved so far.

#### Scenario: User delta over system chain
- **WHEN** a user filament sets only `nozzle_temperature` and inherits `Generic PETG`
- **THEN** the resolved preset has the user's `nozzle_temperature` and `filament_type`
  `PETG` from the system chain

#### Scenario: Missing parent
- **WHEN** a preset inherits a name present in no preset file
- **THEN** resolution fails with `missing_parent` naming the preset and the missing name

### Requirement: Map resolved presets onto profile fields

`import` SHALL write the profile fields mapped from the resolved machine, process and
first filament per the design's mapping table, convert Orca string and percent values to
numbers, write `orca` (app, data dir, machine, process, process purpose, filaments,
`processes` = every process preset compatible with the machine with its name, layer
height, wall loops, infill density and user flag, digest), and re-validate the profile.
`--max-materials N` SHALL set `max_materials` and take precedence over the nozzle count. It SHALL NOT write `fit_clearance_mm`,
`constraints.wall_min_mm`, `constraints.dimension_tolerance_mm`,
`constraints.bridge_max_mm`, `constraints.interface_min_area_mm2`, or
`slicer.preferred_format`. Its JSON output SHALL list written fields, skipped fields with
a reason, and slicer-side compensation settings that are non-zero.

#### Scenario: Overhang angle converted
- **WHEN** the process has `support_threshold_angle` 30
- **THEN** `constraints.overhang_max_deg` is written as 60

#### Scenario: Auto support threshold
- **WHEN** `support_threshold_angle` is 0
- **THEN** `constraints.overhang_max_deg` is unchanged and listed as skipped

#### Scenario: Cruise speed capped by volumetric flow
- **WHEN** `outer_wall_speed` is 200, `filament_max_volumetric_speed` 12, layer height
  0.16 and line width 0.42
- **THEN** `motion.v_cruise_mm_s` is 12 / (0.16 x 0.42) = 178.6

#### Scenario: Toolchanger material slots
- **WHEN** the machine's `nozzle_diameter` has 4 entries
- **THEN** `max_materials` is 4

#### Scenario: AMS slot count given
- **WHEN** the machine has one nozzle and `--max-materials 4` is given
- **THEN** `max_materials` is 4

#### Scenario: Process list populated
- **WHEN** four process presets are compatible with the machine and one is not
- **THEN** `orca.processes` lists exactly the four, each with its layer height

#### Scenario: Calibration fields untouched
- **WHEN** `profile.json` has `fit_clearance_mm.sliding` 0.3 before import
- **THEN** it is 0.3 after import

#### Scenario: Unmapped filament type
- **WHEN** the filament's `filament_type` is `PVA` and no `--material` is given
- **THEN** import fails with `unmapped_material` carrying the raw type and writes nothing

#### Scenario: Slicer hole compensation reported
- **WHEN** the process has `xy_hole_compensation` 0.1
- **THEN** the output lists it under compensation warnings

#### Scenario: No junction deviation derivable
- **WHEN** the machine has no `machine_max_junction_deviation` and its `gcode_flavor` is
  not `klipper`
- **THEN** the `motion` block is not written and is listed as skipped

### Requirement: Select a process preset by print purpose

`select-process --purpose {visual,functional,draft}` SHALL rank the process presets
compatible with the recorded machine by distance of `layer_height` to the purpose's
target fraction of nozzle diameter (visual 0.40, functional 0.50, draft 0.70), break ties
per the design, and return the chosen preset with a one-line reason naming the preset,
layer height and purpose. `--process <name>` SHALL select that preset; with `--purpose`
it records that purpose, without it records `user` with reason "chosen by user". With
`--write`, it SHALL update the process-derived profile fields and
`orca.process` / `orca.process_purpose`.

#### Scenario: Visual purpose on a 0.4 nozzle
- **WHEN** compatible processes have layer heights 0.12, 0.16, 0.20, 0.28 and purpose is
  `visual`
- **THEN** the 0.16 preset is chosen and the reason reads like "selected 0.16mm Standard
  (layer 0.16 mm) for visual quality"

#### Scenario: User override
- **WHEN** `--process "0.20mm Strength @Snapmaker U1 (0.4 nozzle)"` is given
- **THEN** that preset is selected regardless of purpose and the reason says it was
  chosen by the user

#### Scenario: Incompatible preset named
- **WHEN** `--process` names a preset not compatible with the machine
- **THEN** selection fails with `incompatible_process` and writes nothing

### Requirement: Planner re-selects the process for the request's purpose

During Phase 2, when the profile has `orca.processes`, the planner SHALL judge the
request's print purpose, choose a preset from `orca.processes`, and record it as a
planning note `PROCESS: <name> | <purpose> | <why>`. Unless `orca.process_purpose` is
`user`, the main session SHALL apply a choice that differs from `orca.process` with
`select-process --process "<name>" --purpose <purpose> --write` and show the reason line
in the plan summary. A user naming a preset at plan review SHALL be applied with
`--process` and no `--purpose`.

#### Scenario: Decorative request
- **WHEN** the profile's process purpose is `functional` and the request is a decorative
  figurine
- **THEN** the plan summary contains the reason line for a `visual` selection

#### Scenario: User-chosen process kept
- **WHEN** the current process was chosen by the user
- **THEN** the planner does not re-select it

### Requirement: Detect a stale Orca snapshot

`check` SHALL re-resolve the recorded presets and report `fresh` when the digest
matches, `stale` with the list of fields whose mapped value changed, or `unavailable`
when the data dir or a recorded preset is missing. `unavailable` SHALL NOT be an error.
A profile without `orca` SHALL report `not_imported`.

#### Scenario: Preset edited in Orca
- **WHEN** the user changes the recorded process's `layer_height` in Orca after import
- **THEN** `check` reports `stale` listing `motion.layer_height_mm`

#### Scenario: Profile used on another machine
- **WHEN** the recorded data dir does not exist
- **THEN** `check` reports `unavailable` with exit code 0
