## Purpose

Keeps the instruction prose (`SKILL.md`, `commands/`, `skill/`, `prompts/`) in sync with the
repository: referenced paths exist and CLI flags in examples match each script's argparse.
## Requirements
### Requirement: Prose path references resolve
The test suite SHALL verify that every `src/`, `skill/`, `prompts/`, `reference/` and `templates/` path referenced in `SKILL.md`, `commands/*.md`, `skill/*.md` and `prompts/*.md` exists in the repository, ignoring placeholder (`<...>`, `{...}`) and glob (`*`) forms.

#### Scenario: Renamed script
- **WHEN** a script under `src/` is renamed but a prose file still references its old path
- **THEN** the path-reference test fails and names the prose file and the missing path

#### Scenario: Deleted phase file
- **WHEN** a file under `skill/` or `prompts/` is deleted while another prose file still references it
- **THEN** the path-reference test fails naming the dangling reference

#### Scenario: Placeholder path
- **WHEN** prose contains `$SKILL_DIR/src/<script>.py`
- **THEN** the test skips it and does not fail

### Requirement: Prose CLI flags match argparse
The test suite SHALL verify that every `--flag` on a `src/<script>.py` command line inside a fenced bash block of the prose files is defined by an `add_argument` call in that script.

#### Scenario: Removed flag
- **WHEN** a script drops a flag that a fenced bash example in the prose still uses
- **THEN** the flag test fails naming the prose file, script and flag

#### Scenario: Script without literal flags
- **WHEN** a referenced script defines no literal `--flag` arguments
- **THEN** the flag check skips that script

### Requirement: Prose-layer tests are fast
The prose-layer tests SHALL NOT import CadQuery or execute any script.

#### Scenario: Runtime
- **WHEN** `pytest tests/test_prose_layer.py` runs without CadQuery installed
- **THEN** it completes without import errors

### Requirement: Shipped prose references nothing outside the install
The test suite SHALL verify that `SKILL.md`, `commands/*.md`, `skill/*.md`, `prompts/*.md` and `reference/*.md` contain no reference to a repository-only location: `install.sh`, `install.ps1`, `openspec/`, `tests/`, `evals/`, `documentation/`, `TODO.md`, `FILES.md`, `CLAUDE.md`, or a backticked token equal to the name of a directory under `openspec/specs/` (an OpenSpec capability name).

#### Scenario: Capability name cited as a pointer
- **WHEN** `skill/phase3_build.md` contains "see `fem-stress-advisor`" and `openspec/specs/fem-stress-advisor/` exists
- **THEN** the test fails naming the prose file and `fem-stress-advisor`

#### Scenario: Installer script named
- **WHEN** `skill/resume.md` tells the reader to run `install.sh`
- **THEN** the test fails naming the prose file and `install.sh`

#### Scenario: Reference doc cites a dev directory
- **WHEN** `reference/scripts.md` mentions `evals/run_evals.py`
- **THEN** the test fails naming `reference/scripts.md` and the path

#### Scenario: Clean prose
- **WHEN** shipped prose points only at `src/`, `skill/`, `prompts/`, `reference/` and `templates/` paths
- **THEN** the test passes

