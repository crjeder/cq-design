## ADDED Requirements

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
