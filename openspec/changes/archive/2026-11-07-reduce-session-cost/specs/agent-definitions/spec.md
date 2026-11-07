## ADDED Requirements

### Requirement: Each LLM role has an agent definition with minimal tools

The repository SHALL contain `agents/sourcing.md`, `agents/research.md`, `agents/planner.md`, `agents/builder.md` and `agents/auditor.md`. Each SHALL declare `name`, `description`, `tools` and `model` in its frontmatter. `tools` SHALL list only what the role needs: the builder, auditor and planner SHALL NOT include browser, documentation, Artifact, terminal or visualization tools; sourcing and research SHALL add only web search and fetch tools.

#### Scenario: Builder tool list
- **WHEN** `agents/builder.md` is parsed
- **THEN** its `tools` contain `Bash`, `Read`, `Write`, `Edit` and no browser or MCP tool

#### Scenario: Cheap roles default to Sonnet
- **WHEN** the `model` of sourcing, research, builder and auditor is read
- **THEN** each names a Sonnet model, and the planner names the strong model

### Requirement: Spawns use the named agent definitions

`SKILL.md`, `skill/phase*.md` and `commands/*.md` SHALL instruct spawning the role by its agent name and SHALL NOT instruct spawning `general-purpose` for these roles.

#### Scenario: No general-purpose spawn
- **WHEN** a test searches the shipped prose for spawn instructions
- **THEN** none for sourcing, research, planner, builder or auditor names `general-purpose`

### Requirement: Agent files ship with every install mode

The agent files SHALL be present after a plugin install and after a copy install, and SHALL be removed by the installers' uninstall. No install mode SHALL require an external marketplace.

#### Scenario: Local-only install
- **WHEN** a user runs `install.sh` or `install.ps1` on a machine with no network access beyond the checkout
- **THEN** the agents are installed and discoverable without adding a marketplace
