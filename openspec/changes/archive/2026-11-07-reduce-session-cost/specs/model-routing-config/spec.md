## MODIFIED Requirements

### Requirement: A working-directory config names the model for each LLM role

A `skill_config.json` file in the working directory SHALL carry a `models` object with
the keys `planner`, `part_author`, `fix_loop`, `sourcing`, `research`, and `auditor`.
Each value SHALL be either a model id passed verbatim to the spawn or `claude -p`, or
the literal `"inline"`, meaning the role runs in the calling session with no spawn and
no `--model` flag. When a key is absent, a spawned role SHALL use the `model` in its
agent definition.

#### Scenario: Role model is read from the config

- **WHEN** the pipeline is about to dispatch a role and `skill_config.json` exists with
  a value for that role
- **THEN** that value is used as the model for the dispatch, with no skill-file edit
  required to change it

#### Scenario: Inline value suppresses the spawn override

- **WHEN** a role's configured value is `"inline"`
- **THEN** the role runs in the calling session and no `--model` flag or model override
  is passed

#### Scenario: Absent key falls back to the agent file

- **WHEN** `skill_config.json` has no `auditor` key
- **THEN** the auditor runs with the `model` from `agents/auditor.md`

#### Scenario: Recorded model is the real one

- **WHEN** a builder attempt is logged
- **THEN** the `model` field holds the id the builder actually ran on, not a stale default
