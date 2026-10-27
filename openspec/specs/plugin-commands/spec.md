# plugin-commands

## Purpose

The namespaced `/cq-design:*` commands the plugin provides and what each runs.
## Requirements
### Requirement: Namespaced command set

The plugin SHALL provide exactly these commands as files under `commands/`: `design`, `plan`, `edit`, `init`, `update`, `build`, `render`, `status`, invoked as `/cq-design:<name>`. `SKILL.md` SHALL NOT carry a competing command table. (`/cq-design:edit` is specified by the `step-edit-command` capability.)

#### Scenario: Commands listed
- **WHEN** the plugin is enabled
- **THEN** `/cq-design:design`, `:plan`, `:edit`, `:init`, `:update`, `:build`, `:render`, `:status` are offered

### Requirement: design and plan run the pipeline

`/cq-design:design` SHALL run phases 0-4 and `/cq-design:plan` SHALL run phases 1-2 and stop once `BUILD_PLAN.json` is approved. Both SHALL perform the init steps first when `init_permissions.py --check` reports the directory uninitialized.

#### Scenario: Fresh directory
- **WHEN** `/cq-design:design` runs in a directory never initialized
- **THEN** init runs before Phase 0

#### Scenario: Plan only
- **WHEN** `/cq-design:plan` finishes
- **THEN** no part scripts are built

### Requirement: init prepares a working directory

`/cq-design:init` SHALL run `uv sync`, `init_permissions.py`, and profile validation, idempotently, and report any seeded file and validation errors.

#### Scenario: Re-run
- **WHEN** `/cq-design:init` runs twice
- **THEN** the second run changes nothing and overwrites no seeded file

### Requirement: update keeps its existing contract

`/cq-design:update` SHALL satisfy the `update-command` capability unchanged.

#### Scenario: Not a bundled project
- **WHEN** the directory has neither `lib/` nor `.bundle_version.json`
- **THEN** the command stops without creating a bundle

### Requirement: render wraps run_cadquery_model

`/cq-design:render <script.py>` SHALL run `--preview`, reporting the JSON `errors` and their hints. (`/cq-design:build` is specified by the `build-command` capability.)

#### Scenario: Failing script
- **WHEN** `success` is false
- **THEN** the command shows the errors and stops

### Requirement: status is read-only

`/cq-design:status` SHALL report the installed skill version (`skill_version.py`), bundle staleness (`bundle_project.py --check`), and profile validity, and SHALL NOT modify any file.

#### Scenario: Stale bundle
- **WHEN** the project's bundle stamp differs from the installed commit
- **THEN** status reports it and suggests `/cq-design:update`

### Requirement: Init command lines have one copy

The init command lines (`uv sync`, `init_permissions.py`, `printer_profile_validate.py`) SHALL appear only in `commands/init.md`. `SKILL.md` SHALL refer to that file for the once-per-directory setup instead of repeating the commands.

#### Scenario: SKILL.md references init
- **WHEN** `SKILL.md` Prerequisites describes directory setup
- **THEN** it says to run the `/cq-design:init` logic and points to `commands/init.md`
- **AND** it contains no `init_permissions.py` or `printer_profile_validate.py` command line

