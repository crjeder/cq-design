# self-contained-build-environment Specification

## Purpose

Defines how the skill turns the user's working directory into a standalone uv project
during the Build phase: a `pyproject.toml`, `.python-version`, committed `uv.lock`, and the
bundled build tooling, so a user can regenerate all deliverable artifacts with
`uv run python build/build.py` on any machine that has uv, without the skill installed.

## Requirements

### Requirement: The working directory is scaffolded as a standalone uv project

During the Build phase the skill SHALL scaffold the working directory as a self-contained
uv project so the user can regenerate artifacts without the skill installed. It SHALL write
a `pyproject.toml` pinning the runtime dependencies the build tooling imports (cadquery,
trimesh, numpy, lxml, matplotlib, pillow, scipy, networkx, and the `cq-warehouse` git
source) with `requires-python = ">=3.10,<3.13"`, and SHALL write a `.python-version`
selecting a CadQuery-compatible interpreter (3.10-3.12).

#### Scenario: Build phase writes the project files

- **WHEN** the skill runs the Build phase in a working directory
- **THEN** a `pyproject.toml` declaring the runtime dependencies and `requires-python =
  ">=3.10,<3.13"` exists in that working directory
- **AND** a `.python-version` selecting a 3.10-3.12 interpreter exists

#### Scenario: pyproject pins the cq-warehouse git source

- **WHEN** the scaffolded `pyproject.toml` is inspected
- **THEN** it declares `cq-warehouse` under `[tool.uv.sources]` as the same git source used
  by the skill, so the lock resolves to a pinned commit

### Requirement: The build tooling is bundled into the working directory

The skill SHALL bundle the shared build tooling that `build.py` imports into the working
directory so it resolves without a `SKILL_SRC` path or the skill being installed. The
bundle SHALL include the full import closure of `build.py` — the `exporters` and `blocks`
packages (including their data files such as `inventory.json`), `mesh_io`, `model_export`,
`print_orientation`, and `placement`. The bundle SHALL be copied fresh from the skill's
`src/` on each Build-phase run.

#### Scenario: Tooling resolves without the skill installed

- **WHEN** the working directory is copied to a machine that does not have the skill
  installed, and `uv sync` has been run there
- **THEN** `uv run python build/build.py` imports its tooling from the bundled files and
  regenerates the artifacts

#### Scenario: Block data files are bundled

- **WHEN** the bundled `blocks` package is inspected
- **THEN** its data files (`inventory.json`, `inventory_schema.json`) are present alongside
  the `.py` modules

#### Scenario: Re-running the skill refreshes the bundle

- **WHEN** the skill's `src/` tooling has changed and the Build phase is run again in the
  same working directory
- **THEN** the bundled tooling is overwritten with the current `src/` version

### Requirement: The delivered project is synced and locked

After scaffolding the project files and bundling the tooling, the skill SHALL run `uv sync`
in the working directory to create the environment and produce a committed `uv.lock`, and
SHALL verify the build by running `uv run python build/build.py`. The lockfile SHALL pin all
dependency versions, including the `cq-warehouse` commit, so the environment is reproducible.

#### Scenario: Environment is ready after the Build phase

- **WHEN** the Build phase finishes
- **THEN** a `uv.lock` and a synced `.venv` exist in the working directory
- **AND** `uv run python build/build.py` has succeeded as a verification step

#### Scenario: First user run works from the synced environment

- **WHEN** a user runs `uv run python build/build.py` in the delivered working directory
- **THEN** the command uses the already-synced environment and regenerates the artifacts
  without further setup

### Requirement: The uv workflow is documented

The uv workflow SHALL be documented for the user in two places: `build.py`'s module
docstring SHALL describe `uv sync` followed by `uv run python build/build.py` (with the
optional `--plan`/`--parts-dir`/`--out`/`--orientations` flags), and the README's
"Regenerating the 3MF / STL files" section SHALL describe the standalone uv project and the
`uv run python build/build.py` build command.

#### Scenario: build.py docstring documents the build command

- **WHEN** a user reads `build/build.py`'s module docstring
- **THEN** it states that the directory is a uv project and shows `uv sync` and
  `uv run python build/build.py`

#### Scenario: README documents the self-contained build

- **WHEN** a user reads the README's "Regenerating the 3MF / STL files" section
- **THEN** it describes the delivered working directory as a standalone uv project and uses
  `uv run python build/build.py` as the build command
