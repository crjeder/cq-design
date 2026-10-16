## MODIFIED Requirements

### Requirement: Installer path remains supported

`install.sh` and `install.ps1` SHALL keep working unchanged and the README SHALL describe the plugin and the installer as alternatives. The README and `SKILL.md` SHALL state that both install modes provide the skill and the `/cq-design:*` commands (a copy install is loaded by Claude Code as a `skills-dir` plugin), and that they differ in venv location: `<dest>/.venv` from the installer, `${CLAUDE_PLUGIN_DATA}/venv` from `/cq-design:init`. `SKILL.md` SHALL state that `SKILL_DIR` is `${CLAUDE_PLUGIN_ROOT}` in a plugin install and the "Base directory for this skill" path otherwise.

#### Scenario: Installer after plugin files added
- **WHEN** `install.sh` runs
- **THEN** the skill installs as before

#### Scenario: Skill works after a copy install
- **WHEN** the skill is installed with `install.sh --dest <dir>` and its Prerequisites are run with `SKILL_DIR=<dir>/cq-design` and `CLAUDE_PLUGIN_ROOT` unset
- **THEN** `uv sync`, `init_permissions.py`, `printer_profile_validate.py`, and a `run_cadquery_model.py` run all succeed

#### Scenario: Commands after a copy install
- **WHEN** Claude Code starts with the skill copied into `~/.claude/skills/cq-design/`
- **THEN** `/cq-design:design`, `:plan`, `:init`, `:update`, `:build`, `:render`, `:status` are offered and `${CLAUDE_PLUGIN_ROOT}` expands to the copied directory

#### Scenario: Reader checks install modes
- **WHEN** a user reads the README Setup section
- **THEN** it does not claim the installer lacks slash commands
