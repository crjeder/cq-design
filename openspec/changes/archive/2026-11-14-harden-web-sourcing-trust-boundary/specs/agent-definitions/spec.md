## MODIFIED Requirements

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
