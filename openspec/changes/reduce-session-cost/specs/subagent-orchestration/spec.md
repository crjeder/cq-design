## ADDED Requirements

### Requirement: Roles spawn as named agents, not general-purpose

Main SHALL spawn sourcing, research, planner, builder and auditor by their agent definition name. A role's prompt SHALL still be rendered to a file by `src/render_prompt.py` and the spawn SHALL point the agent at that file.

#### Scenario: Auditor spawn
- **WHEN** main starts an implementation audit
- **THEN** it spawns the auditor agent with the path to the rendered audit prompt

### Requirement: Re-audit follows resolved-param changes

After a `parameters.py` edit, the visual audit SHALL re-run only for parts whose resolved params changed, as reported by `plan.py validate`.

#### Scenario: Unaffected part
- **WHEN** a dimension edit leaves part `lid` resolved params unchanged
- **THEN** no new audit is spawned for `lid`
