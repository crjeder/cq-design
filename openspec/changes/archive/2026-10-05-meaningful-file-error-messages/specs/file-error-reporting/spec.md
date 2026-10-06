## ADDED Requirements

### Requirement: Input file failures produce one actionable message
Tool scripts that read a user-supplied or pipeline-produced input file (plan, profile, orientation, config, STL) SHALL, when the file is missing, is a directory, is unreadable, or is not valid JSON where JSON is expected, report a single message naming the file path, the role the file plays, and the cause. They SHALL NOT surface a raw Python traceback for these conditions.

#### Scenario: Missing plan on a --plan CLI
- **WHEN** a CLI that takes `--plan` is run with a path that does not exist
- **THEN** stderr contains one line naming the path and stating the BUILD_PLAN.json was not found, the exit code is 1, and no traceback is printed

#### Scenario: Path is a directory
- **WHEN** an input path points at a directory
- **THEN** the message states a directory was given where a file was expected

#### Scenario: Malformed JSON
- **WHEN** an input JSON file is truncated or invalid
- **THEN** the message names the file and includes the parser's line and column

#### Scenario: Unreadable file
- **WHEN** the OS denies read access
- **THEN** the message names the file and includes the OS reason

### Requirement: STL load errors distinguish missing from invalid
STL loaders SHALL report a nonexistent path differently from a file that exists but cannot be parsed or has no geometry.

#### Scenario: STL not exported yet
- **WHEN** an STL path does not exist
- **THEN** the error says the STL was not found and points at the export step

#### Scenario: Corrupt STL
- **WHEN** the file exists but trimesh cannot parse it
- **THEN** the error says the file is not a valid STL and includes the parser reason

### Requirement: Shared loader
All `--plan` CLIs and the plan/orientation/config reads in `quality_gate.py`, `model_export.py` and `run_cadquery_model.py` SHALL obtain their JSON through the shared helper in `units.py` so the wording is identical across scripts.

#### Scenario: Same message from different scripts
- **WHEN** two different CLIs are given the same missing plan path
- **THEN** both print the same message text
