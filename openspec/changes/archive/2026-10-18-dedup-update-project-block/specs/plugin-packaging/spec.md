## MODIFIED Requirements

### Requirement: Installer path remains supported

`install.sh` and `install.ps1` SHALL keep working and the README SHALL describe the plugin and the installer as alternatives. The README and `SKILL.md` SHALL state that both install modes provide the skill and the `/cq-design:*` commands (a copy install is loaded by Claude Code as a `skills-dir` plugin), and that they differ in venv location: `<dest>/.venv` from the installer, `${CLAUDE_PLUGIN_DATA}/venv` from `/cq-design:init`. `SKILL.md` SHALL state that `SKILL_DIR` is `${CLAUDE_PLUGIN_ROOT}` in a plugin install and the "Base directory for this skill" path otherwise. `SKILL.md` and `skill/` SHALL refer to the installer as "an installer copy" / "reinstall from the repo" without naming `install.sh` or `install.ps1`, since a copy install does not contain them. `skill/resume.md` SHALL refer to refreshing a project's bundled tooling only through `/cq-design:update`, without a duplicated command block.

#### Scenario: Installer after plugin files added
- **WHEN** `install.sh` runs
- **THEN** the skill installs and `.claude-plugin/` is present in the destination

#### Scenario: Skill works after a copy install
- **WHEN** the skill is installed with `install.sh --dest <dir>` and its Prerequisites are run with `SKILL_DIR=<dir>/cq-design` and `CLAUDE_PLUGIN_ROOT` unset
- **THEN** `uv sync`, `init_permissions.py`, `printer_profile_validate.py`, and a `run_cadquery_model.py` run all succeed

#### Scenario: Commands after a copy install
- **WHEN** Claude Code starts with the skill copied into `~/.claude/skills/cq-design/`
- **THEN** `/cq-design:design`, `:plan`, `:init`, `:update`, `:build`, `:render`, `:status` are offered and `${CLAUDE_PLUGIN_ROOT}` expands to the copied directory

#### Scenario: Reader checks install modes
- **WHEN** a user reads the README Setup section
- **THEN** it does not claim the installer lacks slash commands

#### Scenario: Shipped prose does not name the installer scripts
- **WHEN** a reader of a copy install follows `SKILL.md` or `skill/resume.md` to refresh a stale skill
- **THEN** they are told to reinstall from the repo, not to run a script the install lacks

#### Scenario: Resume refresh pointer
- **WHEN** a reader follows `skill/resume.md` to refresh a project's bundled tooling
- **THEN** they are pointed to `/cq-design:update` and no hardcoded `~/.claude/skills/cq-design/src/...` or `<path-to-this-repo>` command appears
