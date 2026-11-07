## MODIFIED Requirements

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
