## ADDED Requirements

### Requirement: Agents ship with the plugin without a marketplace dependency

The plugin SHALL expose `agents/` so its agents load in a plugin install, and `.claude-plugin/marketplace.json` SHALL NOT be required for any install mode. The README SHALL describe local-only installation (installer copy or `--link`, or a local plugin directory).

#### Scenario: Plugin agents available
- **WHEN** the plugin is loaded from the checkout directory
- **THEN** the five role agents are available

#### Scenario: README install modes
- **WHEN** a user reads the README Setup section
- **THEN** a local-only install path is described and no step requires adding a remote marketplace
