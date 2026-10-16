## ADDED Requirements

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
