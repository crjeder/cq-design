## MODIFIED Requirements

### Requirement: Planner runs as a strong-model agent
Phase 2 plan generation SHALL run in a sub-agent whose prompt is the rendered
`prompts/planning.md` and whose model is read from `skill_config.json`'s
`models.planner`, overridden per call; absent that file or key, the strongest
available model. `plan_validate.py` gating and the user approval checkpoint remain in
the main session; validation errors re-enter the planner agent.

#### Scenario: Plan validation loop
- **WHEN** `plan_validate.py` rejects the planner's output
- **THEN** the planner agent is resumed with the validation errors, and the
  user sees only the validated plan summary

#### Scenario: Configured planner model
- **WHEN** `skill_config.json` sets `models.planner`
- **THEN** the planner agent is spawned with that model as its per-call override

## ADDED Requirements

### Requirement: Builder agents use the configured authoring model
A builder agent spawned for an autonomous part SHALL use `skill_config.json`'s
`models.part_author` as its per-call model override; absent that file or key, the
documented mid-tier default. When the value is `"inline"`, the part loop SHALL run in
the calling session instead of spawning a builder agent. The model actually used SHALL
be what Step 5's telemetry record names.

#### Scenario: Configured authoring model
- **WHEN** `models.part_author` names a model and a part routes autonomous
- **THEN** the builder agent is spawned with that model, and its `attempts.jsonl`
  records name that model

#### Scenario: Inline authoring
- **WHEN** `models.part_author` is `"inline"`
- **THEN** no builder agent is spawned and the part loop runs in the main session,
  with telemetry naming the main session's model

### Requirement: One builder agent per part, no verification subagents
A part SHALL be dispatched to at most one builder agent, spawned by the Agent routing
gate. The orchestrating session SHALL NOT spawn additional agents to review, verify,
double-check, or re-run a builder's work. The fresh-context implementation auditor is
the single review agent and the deterministic checks are programs, not agents.

#### Scenario: No verification spawn after a passing builder
- **WHEN** a builder returns `status: passed`
- **THEN** the part proceeds to the implementation audit with no intermediate
  verification agent spawned

#### Scenario: Retry does not spawn a second builder
- **WHEN** a builder's attempt fails or the part is escalated with a user hint
- **THEN** the same builder agent is resumed rather than a second builder spawned for
  that part
