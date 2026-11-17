## ADDED Requirements

### Requirement: sync-profile refreshes Orca-sourced fields

`/cq-design:sync-profile` SHALL run `orca_profile.py import` against the presets recorded
in `profile.json`'s `orca` block, or against `--machine`, `--process` and `--filament`
names the user gives, print each changed field as old -> new, and write the profile. With
no `orca` block and no names given, it SHALL import from the discovered install as init
does. It SHALL NOT write the fields the import excludes.

#### Scenario: Process edited in Orca
- **WHEN** the recorded process's layer height changed in Orca and sync-profile runs
- **THEN** it prints `motion.layer_height_mm` old -> new and the profile holds the new value

#### Scenario: Switch filament
- **WHEN** the user runs sync-profile with `--filament "Generic PLA"`
- **THEN** `material`, `motion.min_layer_time_s` and `orca.filaments` reflect that filament

## MODIFIED Requirements

### Requirement: Namespaced command set

The plugin SHALL provide exactly these commands as files under `commands/`: `design`, `plan`, `edit`, `init`, `update`, `build`, `render`, `status`, `sync-profile`, invoked as `/cq-design:<name>`. `SKILL.md` SHALL NOT carry a competing command table. (`/cq-design:edit` is specified by the `step-edit-command` capability.)

#### Scenario: Commands listed
- **WHEN** the plugin is enabled
- **THEN** `/cq-design:design`, `:plan`, `:edit`, `:init`, `:update`, `:build`, `:render`, `:status`, `:sync-profile` are offered

### Requirement: init prepares a working directory

`/cq-design:init` SHALL run `uv sync`, `init_permissions.py`, and profile validation, idempotently, and report any seeded file and validation errors. When `profile.json` was seeded in this run and `orca_profile.py discover` finds an install, it SHALL ask for the AMS/MMU filament slot count when the machine has one nozzle, run the Orca import (purpose `functional`, `--max-materials` from that answer) and report the imported values, the process selection reason and any compensation warnings. It SHALL also run `install_check.py` and, when `duplicate` is true, warn the user without removing either copy or failing.

#### Scenario: Re-run
- **WHEN** `/cq-design:init` runs twice
- **THEN** the second run changes nothing and overwrites no seeded file

#### Scenario: Duplicate install
- **WHEN** `install_check.py` reports `duplicate` true
- **THEN** init shows the warning and the removal hint and still completes the rest of setup

#### Scenario: No Orca install
- **WHEN** init seeds `profile.json` and no Orca-family install is found
- **THEN** the default profile stays as seeded and init tells the user to edit it

### Requirement: status is read-only

`/cq-design:status` SHALL report the installed skill version (`skill_version.py`), bundle staleness (`bundle_project.py --check`), profile validity, Orca snapshot state (`orca_profile.py check`), and duplicate-install state (`install_check.py`), and SHALL NOT modify any file.

#### Scenario: Stale bundle
- **WHEN** the project's bundle stamp differs from the installed commit
- **THEN** status reports it and suggests `/cq-design:update`

#### Scenario: Duplicate install
- **WHEN** `install_check.py` reports `duplicate` true
- **THEN** status reports both locations and, if `commits_differ`, says the copies are at different commits

#### Scenario: Stale Orca snapshot
- **WHEN** `orca_profile.py check` reports `stale`
- **THEN** status lists the changed fields and suggests `/cq-design:sync-profile`
