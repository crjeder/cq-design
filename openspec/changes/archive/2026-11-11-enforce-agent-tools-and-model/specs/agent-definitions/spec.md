## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Spawns use the named agent definitions

`SKILL.md`, `skill/phase*.md` and `commands/*.md` SHALL instruct spawning each role as the project agent `cq-design-<role>`. They SHALL fall back to the plugin agent `cq-design:<role>` only when the project agent is not offered. They SHALL NOT instruct spawning `general-purpose` for these roles.

#### Scenario: No general-purpose spawn
- **WHEN** a test searches the shipped prose for spawn instructions
- **THEN** none for sourcing, research, planner, builder or auditor names `general-purpose`

#### Scenario: Project agent preferred
- **WHEN** a test reads the spawn instruction for each of the five roles
- **THEN** it names `cq-design-<role>` and gives `cq-design:<role>` only as the fallback
