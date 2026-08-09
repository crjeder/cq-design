# model-routing-config

## Purpose

Defines the working-directory config file that names which model runs each LLM
role in the pipeline (planner, part author, quality-gate fix loop), how it is
seeded, and how a missing config or key falls back rather than failing.

## Requirements

### Requirement: A working-directory config names the model for each LLM role

A `skill_config.json` file in the working directory SHALL carry a `models` object with
the keys `planner`, `part_author`, and `fix_loop`. Each value SHALL be either a model
id passed verbatim to the spawn or `claude -p`, or the literal `"inline"`, meaning the
role runs in the calling session with no spawn and no `--model` flag.

#### Scenario: Role model is read from the config

- **WHEN** the pipeline is about to dispatch a role and `skill_config.json` exists with
  a value for that role
- **THEN** that value is used as the model for the dispatch, with no skill-file edit
  required to change it

#### Scenario: Inline value suppresses the spawn override

- **WHEN** a role's configured value is `"inline"`
- **THEN** the role runs in the calling session and no `--model` flag or model override
  is passed

### Requirement: The config is seeded, never overwritten

`skill/setup.md` SHALL copy `src/skill_config.default.json` to `./skill_config.json`
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
