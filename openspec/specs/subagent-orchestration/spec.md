# subagent-orchestration

## Purpose

Defines how the cq-design pipeline splits work between the main session and
sub-agents: which steps must stay user-facing in the main session, which
steps run in isolated agents (builder, auditor, planner, research), how
escalation and retries are threaded across that boundary, and how the model
that actually executed an attempt is recorded and gated for adoption.

## Requirements

### Requirement: User checkpoints stay in the main session
Every user-facing gate - requirements Q&A, topology clarification, dimension
validation table approval, plan approval, progressive-build stage checkpoints,
design approval, and hint requests after exhausted attempts - SHALL run in the
main session. No sub-agent SHALL be expected to interact with the user.

#### Scenario: Dimension table approval
- **WHEN** the research agent returns the dimension validation table
- **THEN** the main session presents it and waits for user approval or
  corrections before planning begins

#### Scenario: Design approval
- **WHEN** every part has passed its builder and the auditor
- **THEN** the main session displays all final previews and waits for the
  user's approval before print-orientation optimization

### Requirement: Autonomous parts build in isolated builder agents
Each part routed to autonomous build SHALL be built by its own sub-agent whose
prompt is the fully rendered `prompts/part.md` for that part. The builder owns
the full internal loop - write, lint (`script_lint.py`), validate
(`run_cadquery_model.py`), render - for at most 3 attempts, with draft and
refine in the same agent so retries retain attempt memory. The builder SHALL NOT
run a model-driven review of its own render before returning; a part that clears
its deterministic checks and renders SHALL return `status: passed`, and the
fresh-context implementation audit is the acceptance bar for that part.

#### Scenario: Builder return contract
- **WHEN** a builder agent finishes
- **THEN** it returns part id, status (`passed` or `blocked`), bbox, preview
  file paths, attempt count, and an error summary - and no rendered image
  content crosses into the main session

#### Scenario: Retry keeps memory
- **WHEN** attempt 1 fails with a typed error
- **THEN** attempt 2 happens inside the same agent with the prior attempt's
  errors and hints in its context

#### Scenario: Clean deterministic checks end the builder's loop
- **WHEN** an attempt returns `success: true` with no blocking wrapper errors and
  a rendered preview
- **THEN** the builder returns `status: passed` with its bbox and preview paths
  without judging the render itself, and does not spend a further attempt on a
  self-review finding

### Requirement: Progressive parts stay inline
A part routed to progressive build (existing complexity gate: any `interfaces`
entry or >= 3 `blocks_needed`, or a user override) SHALL be built in the main
session with its per-stage user checkpoints, not in a builder agent.

#### Scenario: Routing gate
- **WHEN** a part has an `interfaces` entry
- **THEN** it is built inline with stage checkpoints, and only parts routed
  autonomous are dispatched to builder agents

### Requirement: Blocked escalation resumes the same agent
When a builder exhausts its 3 attempts, it SHALL return `blocked` with an error
summary; the main session SHALL ask the user (hint, accept as-is, or skip); on
a hint, the SAME builder agent SHALL be resumed with the hint rather than a new
agent spawned.

#### Scenario: Hint after exhaustion
- **WHEN** the user provides a hint for a blocked part
- **THEN** the original builder agent is resumed with the hint and its attempt
  history intact

### Requirement: Fresh-context implementation audit
A part accepted by its builder SHALL be judged by an auditor agent that
receives the part's `BUILD_PLAN.json` entry and the rendered preview, section,
and detail images, and SHALL NOT receive the part script. The auditor answers
the Visual Review Checklist questions, each against a specific cited view. An
audit failure re-enters that part's builder as a targeted `visual_mismatch`
fix.

#### Scenario: Auditor input isolation
- **WHEN** the auditor agent is spawned for a part
- **THEN** its prompt contains the plan entry and image paths but no part
  script source

#### Scenario: Audit failure
- **WHEN** the auditor answers any checklist question "no"
- **THEN** it names the question, the cited view, and the discrepancy, and the
  part's builder is resumed with that finding

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

### Requirement: Dimension lookup runs as a research agent
When Phase 1 requires real-world dimension lookups, the lookup workflow (web
search, spec pages, community model pages, STL download + `measure_stl.py`)
SHALL run in a research agent that returns only the dimension validation table
(value, source, status per row) and source URLs. When no lookup is needed, no
research agent is spawned.

#### Scenario: Heavy pages stay in the agent
- **WHEN** the research agent browses spec pages and model listings
- **THEN** the main session receives the validation table and sources, not page
  snapshots

### Requirement: Telemetry records the executing model
Every `attempts.jsonl` record SHALL carry the model that actually executed the
attempt (the builder agent's model, or the main-session model for inline
builds) in its `model` field instead of the constant `"inline"`.

#### Scenario: Routed build attempt
- **WHEN** a builder agent running on a mid-tier model logs attempt 2
- **THEN** the record's `model` field names that model

### Requirement: Adoption is eval-gated
The sub-agent routing SHALL be compared against the inline baseline using
`evals/run_evals.py` scorecards (first-shot rate, attempts-to-pass, cost per
accepted part, Chamfer distance) before and after the change. A worse
scorecard blocks adoption until fixed or the change is reverted.

#### Scenario: Scorecard regression
- **WHEN** the post-change scorecard shows higher cost per accepted part and no
  offsetting quality gain
- **THEN** the routing does not ship as the default
