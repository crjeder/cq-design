# agent-definitions

## Purpose

TBD - Per-role agent definitions with minimal tool lists and model defaults, shipped with every install mode.

## Requirements

### Requirement: Each LLM role has an agent definition with minimal tools

The repository SHALL contain `agents/sourcing.md`, `agents/research.md`, `agents/planner.md`, `agents/builder.md` and `agents/auditor.md`. Each SHALL declare `name`, `description`, `tools` and `model` in its frontmatter. `tools` SHALL list only what the role needs: the builder, auditor and planner SHALL NOT include browser, documentation, Artifact, terminal or visualization tools. The sourcing agent's `tools` SHALL be exactly `Read`, `WebSearch` and `WebFetch`. The research agent's `tools` SHALL be exactly `Read`, `Bash`, `WebSearch` and `WebFetch`. Neither web-reading agent SHALL include `Write`, `Edit`, `Glob`, `Grep` or any MCP tool.

#### Scenario: Builder tool list
- **WHEN** `agents/builder.md` is parsed
- **THEN** its `tools` contain `Bash`, `Read`, `Write`, `Edit` and no browser or MCP tool

#### Scenario: Cheap roles default to Sonnet
- **WHEN** the `model` of sourcing, research, builder and auditor is read
- **THEN** each names a Sonnet model, and the planner names the strong model

#### Scenario: Sourcing tool list
- **WHEN** `agents/sourcing.md` is parsed
- **THEN** its `tools` are exactly `Read`, `WebSearch` and `WebFetch`

#### Scenario: Research tool list
- **WHEN** `agents/research.md` is parsed
- **THEN** its `tools` are exactly `Read`, `Bash`, `WebSearch` and `WebFetch`

### Requirement: Spawns use the named agent definitions

`SKILL.md`, `skill/phase*.md` and `commands/*.md` SHALL instruct spawning each role as the project agent `cq-design-<role>`. They SHALL fall back to the plugin agent `cq-design:<role>` only when the project agent is not offered. They SHALL NOT instruct spawning `general-purpose` for these roles.

#### Scenario: No general-purpose spawn
- **WHEN** a test searches the shipped prose for spawn instructions
- **THEN** none for sourcing, research, planner, builder or auditor names `general-purpose`

#### Scenario: Project agent preferred
- **WHEN** a test reads the spawn instruction for each of the five roles
- **THEN** it names `cq-design-<role>` and gives `cq-design:<role>` only as the fallback

### Requirement: Setup installs project-level agent copies

`src/init_permissions.py` SHALL copy each shipped `agents/<role>.md` to `./.claude/agents/cq-design-<role>.md` in the working directory. A copy whose content differs from the shipped file SHALL be overwritten. A copy that is already identical SHALL be left untouched. Files in `.claude/agents/` that do not match one of the five `cq-design-<role>.md` names SHALL NOT be touched. Each copy's frontmatter `name` SHALL equal its filename stem.

#### Scenario: Fresh project gets all five agents
- **WHEN** init runs in a directory with no `.claude/agents/`
- **THEN** `.claude/agents/` holds `cq-design-sourcing.md`, `cq-design-research.md`, `cq-design-planner.md`, `cq-design-builder.md` and `cq-design-auditor.md`, each byte-identical to its shipped source

#### Scenario: Stale copy is refreshed
- **WHEN** init runs and `.claude/agents/cq-design-builder.md` differs from `agents/builder.md`
- **THEN** the copy is overwritten with the shipped content and init reports it

#### Scenario: User agents are left alone
- **WHEN** init runs and `.claude/agents/my-reviewer.md` exists
- **THEN** that file is byte-identical afterwards

### Requirement: Agent files ship with every install mode

The agent files SHALL be present after a plugin install and after a copy install, and SHALL be removed by the installers' uninstall. No install mode SHALL require an external marketplace.

#### Scenario: Local-only install
- **WHEN** a user runs `install.sh` or `install.ps1` on a machine with no network access beyond the checkout
- **THEN** the agents are installed and discoverable without adding a marketplace
