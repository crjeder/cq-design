## ADDED Requirements

### Requirement: Post-acceptance advisors run in the orchestrator only
The FEM stress advisor and the toolpath-speed advisor SHALL be run by the orchestrating
session after a part's script is accepted, as described in `skill/phase3_build.md`.
`prompts/part.md` SHALL NOT instruct the builder to run either advisor. It SHALL keep one
instruction that, when the orchestrator supplies a FEM result for the part, the result's
failure index and location replace the closed-form `check` and `worst_case_stress` in the
engineering rationale.

#### Scenario: Builder prompt has no advisor commands
- **WHEN** `render_prompt.py builder` renders a part's prompt
- **THEN** the prompt contains no `fem_check.py` or `toolpath_speed.py` command

#### Scenario: FEM result reaches the rationale through the orchestrator
- **WHEN** the orchestrator's FEM run for an accepted part returns `status: "ok"` and the
  builder is resumed
- **THEN** the builder cites the failure index and location in `check` and
  `worst_case_stress` instead of a closed-form derivation
