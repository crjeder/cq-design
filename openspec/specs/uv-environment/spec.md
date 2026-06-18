# Spec: uv-environment

## Purpose

Defines how the project environment is set up and managed using uv, ensuring consistent,
reproducible installs across machines with a single command.

## Requirements

### Requirement: Single-command environment setup
The project SHALL be installable with `uv sync` on a clean clone, with no prior manual steps beyond having uv installed.

#### Scenario: Fresh clone on machine with uv but no Python 3.12
- **WHEN** a user runs `uv sync` in the project root after cloning
- **THEN** uv downloads CPython 3.12, creates a `.venv`, and installs all runtime and dev dependencies

#### Scenario: Fresh clone on machine with Python 3.13 only
- **WHEN** a user runs `uv sync`
- **THEN** uv uses `.python-version` to select 3.12 (downloading if needed) rather than the system 3.13, and the install succeeds

### Requirement: Python version constraint is enforced
The project SHALL declare `requires-python = ">=3.10,<3.13"` so that uv rejects incompatible interpreters with a clear error before attempting to install CadQuery.

#### Scenario: User attempts install with Python 3.13+
- **WHEN** uv resolves dependencies and the only available interpreter is 3.13+
- **THEN** uv emits an error referencing the `requires-python` constraint and does not proceed

### Requirement: Dependency versions are reproducible
All dependency versions, including the `cq_warehouse` git source, SHALL be pinned in a committed `uv.lock` file so that two clones on different dates produce identical environments.

#### Scenario: Two users clone the repo a month apart
- **WHEN** both run `uv sync`
- **THEN** both install the exact same package versions, including the same `cq_warehouse` git commit SHA

### Requirement: Dev dependencies are declared and installed by default
pytest SHALL be declared in a `[dependency-groups] dev` group. `uv sync` SHALL install dev dependencies unless `--no-dev` is passed.

#### Scenario: Running tests after uv sync
- **WHEN** a user runs `uv sync` then `uv run pytest tests/`
- **THEN** pytest is available and all tests pass

### Requirement: requirements.txt is removed
The project SHALL NOT contain a `requirements.txt` file. `pyproject.toml` is the single source of dependency truth.

#### Scenario: User looks for requirements.txt
- **WHEN** a user checks the repo root
- **THEN** no `requirements.txt` is present; `pyproject.toml` contains all dependency information
