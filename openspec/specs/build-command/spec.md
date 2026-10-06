# build-command Specification

## Purpose

Defines `/cq-design:build [format]`, the command that runs the project's `build/build.py`.

## Requirements

### Requirement: /cq-design:build generates model files in the requested format

The plugin SHALL provide `commands/build.md`, invoked as `/cq-design:build [format]`, which
runs the working directory's `build/build.py` with `uv run python`. With a `format` argument
it SHALL pass `--formats <format>`; without one it SHALL pass no `--formats` so `build.py`
uses the profile's preferred format. It SHALL report the files `build.py` wrote or, on a
non-zero exit, the error output. It SHALL NOT replace `build.py`'s logic. The plugin SHALL
NOT provide a `deliver` command.

#### Scenario: Format given

- **WHEN** the user runs `/cq-design:build step`
- **THEN** `uv run python build/build.py --formats step` runs in the working directory

#### Scenario: No format given

- **WHEN** the user runs `/cq-design:build`
- **THEN** `build.py` runs without `--formats` and writes the preferred format

#### Scenario: Project not initialised

- **WHEN** `build/build.py` does not exist in the working directory
- **THEN** the command reports that and points to `/cq-design:init` or `/cq-design:update`
  without running anything else

#### Scenario: Deliver command is gone

- **WHEN** the plugin's commands are listed
- **THEN** `build` is offered and `deliver` is not
