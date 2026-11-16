## MODIFIED Requirements

### Requirement: A working-directory config names the model for each LLM role

A `skill_config.json` file in the working directory SHALL carry a `models` object with
the keys `planner`, `part_author`, `fix_loop`, `sourcing`, `research`, `auditor`, and
`oracle`. Each value SHALL be either a model id or the literal `"inline"`. A model id is
passed to `claude -p --model` verbatim. `"inline"` means the role runs in the calling
session, with no spawn and no `--model` flag. When a key is absent, the role SHALL use the
value in the shipped `src/skill_config.default.json`. The agent file's `model:` SHALL NOT
be relied on, because hosts may ignore it.

#### Scenario: Role model is read from the config

- **WHEN** the pipeline is about to dispatch a role and `skill_config.json` exists with
  a value for that role
- **THEN** that value is used as the model for the dispatch, with no skill-file edit
  required to change it

#### Scenario: Inline value suppresses the spawn override

- **WHEN** a role's configured value is `"inline"`
- **THEN** the role runs in the calling session and no `--model` flag or model override
  is passed

#### Scenario: Absent key falls back to the shipped default

- **WHEN** `skill_config.json` has no `auditor` key
- **THEN** the render output's `model` is `models.auditor` from
  `src/skill_config.default.json`

#### Scenario: Recorded model is the real one

- **WHEN** a builder attempt is logged
- **THEN** the `model` field holds the id the builder actually ran on, not a stale default

#### Scenario: Oracle default

- **WHEN** `render_prompt.py oracle` runs with no `skill_config.json`
- **THEN** the output's `model` is `models.oracle` from `src/skill_config.default.json`,
  a Sonnet id, and `agent_model` is `sonnet`

### Requirement: Every spawn passes the model explicitly

`src/render_prompt.py` SHALL include `agent_model` in its JSON output for every prompt
kind whose role resolves to a model id. `agent_model` SHALL be the Agent-tool alias for
that id: the first of `fable`, `opus`, `sonnet`, `haiku` contained in the id, or else
the id unchanged. The spawn instruction for every role SHALL pass `agent_model` as the
Agent tool's `model` parameter.

#### Scenario: Sonnet id maps to the alias
- **WHEN** `models.part_author` is `claude-sonnet-5-5` and the part prompt is rendered
- **THEN** the output has `"model": "claude-sonnet-5-5"` and `"agent_model": "sonnet"`

#### Scenario: Unknown family passes through
- **WHEN** a role's model id contains none of the four family names
- **THEN** `agent_model` equals the id

#### Scenario: Spawn prose passes the alias
- **WHEN** a test reads the spawn instruction for each of the six roles
- **THEN** it says to pass the render output's `agent_model` as the Agent tool's `model`
