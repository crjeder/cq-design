# staged-validate-args

## Purpose

TBD - created by archiving change expected-dims-final-stage. Update Purpose after archive.

## Requirements

### Requirement: Expected-dimension checking runs only on a part's final build stage

`render_prompt.py` SHALL compute the `run_cadquery_model.py` validate command
separately for each stage in a part's build (`profile_stub`, `base_shape`,
`features`, `finishing`, or the single `full` stage), and SHALL include
`--expected-dims` and `--dim-tolerance` only in the command for that part's
final stage. Every other validate arg (`--wall-min`, `--strict`, `--preview`,
callouts, sections, `--attempts-log`) SHALL be present at every stage as
before.

#### Scenario: Staged part validates without dimension checking on early stages

- **WHEN** a part builds the staged sequence `base_shape`, `features`, `finishing`
- **THEN** the `base_shape` and `features` validate commands omit
  `--expected-dims` and `--dim-tolerance`, and the `finishing` validate
  command includes them

#### Scenario: Non-staged part validates with dimension checking on its only stage

- **WHEN** a part builds the single `full` stage
- **THEN** the `full` validate command includes `--expected-dims` and
  `--dim-tolerance`

#### Scenario: profile_stub never carries dimension checking

- **WHEN** a part's stage list starts with `profile_stub`
- **THEN** the `profile_stub` validate command omits `--expected-dims` and
  `--dim-tolerance`, since it is never the final stage

### Requirement: The builder prompt shows the per-stage validate command

`prompts/builder.md`'s Commands section SHALL present the validate command for
each stage in `{{STAGES}}`, rather than one command reused across every stage.
`prompts/builder.md` SHALL NOT instruct the builder to disregard a
`dimension_mismatch` error on a non-final stage, since that stage's validate
command no longer requests dimension checking.

#### Scenario: Builder prompt has no dimension_mismatch exception

- **WHEN** `prompts/builder.md` is rendered for any part
- **THEN** it contains no instruction to ignore or carry on past a
  `dimension_mismatch` error type
