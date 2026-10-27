## MODIFIED Requirements

### Requirement: Namespaced command set

The plugin SHALL provide exactly these commands as files under `commands/`: `design`, `plan`, `edit`, `init`, `update`, `build`, `render`, `status`, invoked as `/cq-design:<name>`. `SKILL.md` SHALL NOT carry a competing command table. (`/cq-design:edit` is specified by the `step-edit-command` capability.)

#### Scenario: Commands listed
- **WHEN** the plugin is enabled
- **THEN** `/cq-design:design`, `:plan`, `:edit`, `:init`, `:update`, `:build`, `:render`, `:status` are offered
