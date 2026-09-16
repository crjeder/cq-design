## MODIFIED Requirements

### Requirement: Planner runs as a strong-model agent
Phase 2 plan generation SHALL run in a sub-agent whose prompt is the rendered
`prompts/planning.md` and whose model is read from `skill_config.json`'s
`models.planner`, overridden per call; absent that file or key, the strongest
available model. The planner agent SHALL write `BUILD_PLAN.json` to the working
directory itself and run `plan_validate.py` itself via Bash, retrying against its own
validation errors up to a bounded number of attempts (matching the builder agent's
3-attempt convention), before returning. The user approval checkpoint (`plan_summary.py`
run against the file the agent wrote) remains in the main session.

#### Scenario: Plan validation loop stays inside the planner agent
- **WHEN** `plan_validate.py` rejects the planner's first write of `BUILD_PLAN.json`
- **THEN** the planner agent itself reruns `plan_validate.py` after fixing the plan,
  inside the same agent invocation, without the main session parsing or re-supplying the
  plan JSON

#### Scenario: Planner returns a status summary, not plan JSON
- **WHEN** the planner agent finishes (validated or exhausted its retry attempts)
- **THEN** its final message is a status summary (validity, part count, and any items
  needing a user decision) and the main session reads `BUILD_PLAN.json` from disk rather
  than parsing plan content out of the agent's reply

#### Scenario: Exhausted retries escalate to the user
- **WHEN** the planner agent still cannot produce a valid plan after its bounded retry
  attempts
- **THEN** it returns `blocked` with the remaining validator errors, the main session
  asks the user, and resumes the same planner agent with the answer rather than spawning
  a new one

#### Scenario: Configured planner model
- **WHEN** `skill_config.json` sets `models.planner`
- **THEN** the planner agent is spawned with that model as its per-call override
