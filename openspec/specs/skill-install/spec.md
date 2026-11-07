# skill-install

## Purpose

A cross-platform installer that places the cq-design skill in the Claude Code
personal skills directory and provisions its Python environment, with idempotent
re-install and uninstall support.
## Requirements
### Requirement: One-command install into the skills directory

The installer SHALL place the cq-design skill into the Claude Code personal
skills directory so Claude Code can discover it. The default destination SHALL
be `~/.claude/skills/cq-design/`, overridable via a destination flag or the
`CLAUDE_SKILLS_DIR` environment variable. A copy install SHALL contain only an
explicit allowlist of repository entries: `SKILL.md`, `.claude-plugin/`,
`agents/`, `commands/`, `skill/`, `prompts/`, `reference/`, `src/`, `templates/`,
`pyproject.toml`, `uv.lock`, `.python-version`, and `LICENSE`. Within the copied
entries, `__pycache__/`, `*.egg-info/`, and `.fossil/` directories SHALL be
pruned. `install.sh` and `install.ps1` SHALL carry the same allowlist. The
installer SHALL NOT require network access to any marketplace. If Claude Code
does not load `agents/` from the destination, the installer SHALL also copy the
agent files to the personal agents directory and `--uninstall` SHALL remove them.

#### Scenario: Fresh install to default location

- **WHEN** a user runs the installer with no existing install present
- **THEN** the skill's `SKILL.md`, `skill/`, `src/`, `prompts/`, `reference/`, and
  `agents/` are placed under `~/.claude/skills/cq-design/`
- **AND** the installer reports the destination path on success

#### Scenario: Custom destination

- **WHEN** a user sets `CLAUDE_SKILLS_DIR` or passes a destination flag
- **THEN** the skill is installed under that directory instead of the default

#### Scenario: Throwaway artifacts excluded

- **WHEN** the installer copies the skill from a checkout that also holds
  `TODO.md`, `documentation/`, `tests/`, `evals/`, `openspec/`, `CLAUDE.md`,
  `FILES.md`, `README.md`, `.git`, `.venv`, `build/`, `BUILD_PLAN.json`, and the
  installer scripts
- **THEN** none of those are present in the destination
- **AND** every allowlisted entry present in the checkout is present in the
  destination

#### Scenario: Dev artifacts inside src are pruned

- **WHEN** the checkout's `src/` contains `cq_design_skill.egg-info/`, `.fossil/`,
  or `__pycache__/` directories
- **THEN** none of them are present under the destination's `src/`

#### Scenario: Installers agree

- **WHEN** the test suite compares the allowlists in `install.sh` and
  `install.ps1`
- **THEN** they name the same entries

#### Scenario: Uninstall removes agent copies

- **WHEN** the installer ran with the agents-directory copy and `--uninstall` runs
- **THEN** the copied agent files are removed along with the skill directory

### Requirement: Environment provisioning

The installer SHALL provision the Python environment in the installed location
by running `uv sync` with the destination as the project directory, producing a
working `.venv` there.

#### Scenario: uv present

- **WHEN** `uv` is on PATH and the install proceeds
- **THEN** the installer runs `uv sync` in the destination
- **AND** exits zero only if `uv sync` succeeds

#### Scenario: uv missing

- **WHEN** `uv` is not found on PATH
- **THEN** the installer prints a message naming `uv` and its install URL
- **AND** exits non-zero WITHOUT modifying the skills directory

### Requirement: Idempotent re-install

Re-running the installer SHALL update an existing cq-design install in place
without requiring manual cleanup, replacing only the cq-design skill files.

#### Scenario: Re-install over existing copy

- **WHEN** a user runs the installer and `~/.claude/skills/cq-design/` already
  exists
- **THEN** the cq-design skill files are refreshed to match the current repo
- **AND** other skills in the skills directory are left untouched

### Requirement: Link mode for contributors

The installer SHALL support a link mode that symlinks the repo into the skills
directory instead of copying, so repo edits are reflected live.

#### Scenario: Link mode requested

- **WHEN** a user runs the installer with the link flag
- **THEN** `~/.claude/skills/cq-design/` is a symlink to the repository
- **AND** if the platform denies symlink creation, the installer reports a clear
  error and exits non-zero

### Requirement: Uninstall

The installer SHALL provide a way to remove the installed skill, deleting only
`~/.claude/skills/cq-design/`.

#### Scenario: Uninstall removes the skill

- **WHEN** a user runs the uninstall path
- **THEN** `~/.claude/skills/cq-design/` is removed
- **AND** no other skill directories are affected

### Requirement: Cross-platform entry points

The installer SHALL provide a POSIX shell entry point for macOS/Linux and a
PowerShell entry point for Windows, each self-contained with no dependency on
the other platform's shell.

#### Scenario: POSIX install

- **WHEN** a macOS or Linux user runs the shell installer
- **THEN** the install completes using only POSIX shell and `uv`

#### Scenario: Windows install

- **WHEN** a Windows user runs the PowerShell installer
- **THEN** the install completes using only PowerShell and `uv`

