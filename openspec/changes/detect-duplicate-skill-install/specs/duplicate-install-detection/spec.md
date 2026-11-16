## ADDED Requirements

### Requirement: Report a duplicate install

`src/install_check.py` SHALL report whether the cq-design plugin and the standalone skill are both installed. The plugin is found through `installed_plugins.json` in the Claude config directory (an entry named `cq-design` whose `installPath` exists); the standalone skill is found at `<skills dir>/cq-design/SKILL.md`. The script SHALL emit JSON with `plugin`, `standalone` (each `null` or an object with `path` and `commit`), `duplicate`, `commits_differ`, and `hint`, SHALL exit 0, and SHALL NOT modify any file.

#### Scenario: Both installed
- **WHEN** both the plugin entry and the standalone `SKILL.md` exist
- **THEN** `duplicate` is true and `hint` names both paths and how to remove one

#### Scenario: Only one installed
- **WHEN** only the plugin, or only the standalone skill, exists
- **THEN** `duplicate` is false and `hint` is empty

#### Scenario: Commits differ
- **WHEN** both are installed and both commits are known and unequal
- **THEN** `commits_differ` is true

#### Scenario: Plugin registry missing or unreadable
- **WHEN** `installed_plugins.json` is absent or not valid JSON
- **THEN** `plugin` is `null` and the script still exits 0
