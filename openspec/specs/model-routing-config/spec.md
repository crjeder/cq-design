# model-routing-config

## Purpose

Defines the working-directory config file that names which model runs each LLM
role in the pipeline (planner, part author, quality-gate fix loop), how it is
seeded, and how a missing config or key falls back rather than failing.

## Requirements

### Requirement: A working-directory config names the model for each LLM role

A `skill_config.json` file in the working directory SHALL carry a `models` object with
the keys `planner`, `part_author`, `fix_loop`, `sourcing`, `research`, and `auditor`.
Each value SHALL be either a model id or the literal `"inline"`. A model id is passed to
`claude -p --model` verbatim. `"inline"` means the role runs in the calling session,
with no spawn and no `--model` flag. When a key is absent, the role SHALL use the value
in the shipped `src/skill_config.default.json`. The agent file's `model:` SHALL NOT be
relied on, because hosts may ignore it.

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
- **WHEN** a test reads the spawn instruction for each of the five roles
- **THEN** it says to pass the render output's `agent_model` as the Agent tool's `model`

### Requirement: The config is seeded, never overwritten

`src/init_permissions.py` SHALL copy `src/skill_config.default.json` to `./skill_config.json`
only when no `skill_config.json` exists in the working directory, mirroring the
`printer_profile.json` seeding step. An existing file SHALL NOT be overwritten,
re-seeded, or merged.

#### Scenario: Fresh directory is seeded

- **WHEN** setup runs in a directory with no `skill_config.json`
- **THEN** the shipped default is copied in and the user is told it can be edited

#### Scenario: Existing config survives setup

- **WHEN** setup runs in a directory whose `skill_config.json` has a user-edited
  `models.part_author`
- **THEN** the file is left byte-identical and the user's value is what the pipeline
  reads

### Requirement: A missing config falls back, it does not fail

A missing `skill_config.json`, a missing `models` object, or a missing role key SHALL
NOT abort the pipeline or the quality gate. Each affected role SHALL fall back to its
documented default: strongest available for `planner`, mid-tier for `part_author`, and
`inline` for `fix_loop`.

#### Scenario: Pipeline runs in an unseeded directory

- **WHEN** Phase 2 or Phase 3 runs and no `skill_config.json` exists
- **THEN** the phase dispatches its agent on the documented fallback tier rather than
  reporting a configuration error

#### Scenario: Gate fix loop without a config

- **WHEN** `quality_gate.py --fix` runs and no `skill_config.json` exists
- **THEN** `claude -p` is invoked with no `--model` flag, exactly as before this change
