# plugin-packaging

## Purpose

Packages the cq-design skill as an installable Claude Code plugin with a persistent Python environment.

## Requirements

### Requirement: Repository is an installable Claude Code plugin

The repository SHALL contain `.claude-plugin/plugin.json` naming the plugin `cq-design` and exposing the root `SKILL.md` as its skill, and `.claude-plugin/marketplace.json` listing the plugin with the repository root as its source. Existing skill files SHALL NOT be moved.

#### Scenario: Manifest validates
- **WHEN** `claude plugin validate .` runs at the repository root
- **THEN** it reports no errors

#### Scenario: Install from marketplace
- **WHEN** a user adds the repository as a marketplace and installs `cq-design`
- **THEN** the cq-design skill and the `/cq-design:*` commands are available

### Requirement: Scripts resolve from the plugin root

Every command and the skill's Prerequisites SHALL reference tooling via the plugin root path (`${CLAUDE_PLUGIN_ROOT}`) and SHALL NOT rely on the shell working directory or on a shell variable exported by Claude Code.

#### Scenario: Run from a project directory
- **WHEN** a command runs with the user's project as working directory
- **THEN** every `src/` script path in it is the absolute plugin root path

### Requirement: Python environment persists across plugin updates

The Python virtual environment SHALL live under `${CLAUDE_PLUGIN_DATA}`, selected with `UV_PROJECT_ENVIRONMENT`, and SHALL NOT be created inside the plugin root.

#### Scenario: Plugin updated
- **WHEN** the plugin updates to a new version
- **THEN** the existing venv is reused and `uv sync` only reconciles changed dependencies

### Requirement: Installer path remains supported

`install.sh` and `install.ps1` SHALL keep working unchanged and the README SHALL describe the plugin and the installer as alternatives.

#### Scenario: Installer after plugin files added
- **WHEN** `install.sh` runs
- **THEN** the skill installs as before
