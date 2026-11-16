## MODIFIED Requirements

### Requirement: Each LLM role has an agent definition with minimal tools

The repository SHALL contain `agents/sourcing.md`, `agents/research.md`, `agents/planner.md`, `agents/builder.md`, `agents/auditor.md` and `agents/oracle.md`. Each SHALL declare `name`, `description`, `tools` and `model` in its frontmatter. `tools` SHALL list only what the role needs: the builder, auditor and planner SHALL NOT include browser, documentation, Artifact, terminal or visualization tools. The sourcing agent's `tools` SHALL be exactly `Read`, `WebSearch` and `WebFetch`. The research agent's `tools` SHALL be exactly `Read`, `Bash`, `WebSearch` and `WebFetch`. Neither web-reading agent SHALL include `Write`, `Edit`, `Glob`, `Grep` or any MCP tool. The oracle agent's `tools` SHALL be exactly `Read`, `Write` and `Bash`.

#### Scenario: Builder tool list
- **WHEN** `agents/builder.md` is parsed
- **THEN** its `tools` contain `Bash`, `Read`, `Write`, `Edit` and no browser or MCP tool

#### Scenario: Cheap roles default to Sonnet
- **WHEN** the `model` of sourcing, research, builder, auditor and oracle is read
- **THEN** each names a Sonnet model, and the planner names the strong model

#### Scenario: Sourcing tool list
- **WHEN** `agents/sourcing.md` is parsed
- **THEN** its `tools` are exactly `Read`, `WebSearch` and `WebFetch`

#### Scenario: Research tool list
- **WHEN** `agents/research.md` is parsed
- **THEN** its `tools` are exactly `Read`, `Bash`, `WebSearch` and `WebFetch`

#### Scenario: Oracle tool list
- **WHEN** `agents/oracle.md` is parsed
- **THEN** its `tools` are exactly `Read`, `Write` and `Bash`

### Requirement: Spawns use the named agent definitions

`SKILL.md`, `skill/phase*.md` and `commands/*.md` SHALL instruct spawning each role as the project agent `cq-design-<role>`. They SHALL fall back to the plugin agent `cq-design:<role>` only when the project agent is not offered. They SHALL NOT instruct spawning `general-purpose` for these roles.

#### Scenario: No general-purpose spawn
- **WHEN** a test searches the shipped prose for spawn instructions
- **THEN** none for sourcing, research, planner, builder, auditor or oracle names `general-purpose`

#### Scenario: Project agent preferred
- **WHEN** a test reads the spawn instruction for each of the six roles
- **THEN** it names `cq-design-<role>` and gives `cq-design:<role>` only as the fallback
