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
the full internal loop - write steps, lint (`script_lint.py`), run
(`step_worker.py run`), fix the failing step or restore a snapshot - with draft and
refine in the same agent so retries retain memory. Step failures SHALL NOT be
limited by an attempt count; the loop ends when every step and the full tier pass,
or when the step report sets `probe_stuck: true`. The builder SHALL NOT run a
model-driven review of its own render before returning; a part that clears its
deterministic checks and renders SHALL return `status: passed`, and the
fresh-context implementation audit is the acceptance bar for that part.

#### Scenario: Builder return contract
- **WHEN** a builder agent finishes
- **THEN** it returns part id, status (`passed` or `blocked`), bbox, preview
  file paths, attempt count, the last step report, and an error summary - and no
  rendered image content crosses into the main session

#### Scenario: Retry keeps memory
- **WHEN** a step fails with a probe failure
- **THEN** the next run happens inside the same agent with the prior step report in its
  context

#### Scenario: Step failures do not exhaust the builder
- **WHEN** the builder has had six failing step runs, none with `probe_stuck: true`
- **THEN** it keeps iterating and does not return `blocked`

#### Scenario: Clean deterministic checks end the builder's loop
- **WHEN** every step passes and the full-tier result is `success: true` with no
  blocking wrapper errors and a rendered preview
- **THEN** the builder returns `status: passed` with its bbox and preview paths
  without judging the render itself, and does not spend a further run on a
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
When a step report sets `probe_stuck: true`, or the part needs a block or primitive the
inventory does not provide, the builder SHALL return `blocked` with reason
`probe_stuck` or `missing_block` and an error summary naming the probe or the missing
geometry; the main session SHALL ask the user (plan change, hint, accept as-is, or
skip); on a plan change or a hint, the SAME builder agent SHALL be resumed rather than a
new agent spawned.

#### Scenario: Hint after exhaustion
- **WHEN** the user provides a hint for a part blocked with `probe_stuck` or
  `missing_block`
- **THEN** the original builder agent is resumed with the hint and its step history
  intact, not a new agent

#### Scenario: Hint after a stuck probe
- **WHEN** the user provides a hint for a part blocked with `probe_stuck`
- **THEN** the original builder agent is resumed with the hint and its step history
  intact

#### Scenario: Plan change after a stuck probe
- **WHEN** the user changes the plan entry the stuck probe came from
- **THEN** the change is logged in `request_log`, the attempt count for that part
  increases by one, and the same builder is resumed

### Requirement: Fresh-context implementation audit
A part accepted by its builder SHALL be judged by an auditor agent that
receives the part's `BUILD_PLAN.json` entry, the rendered preview, section, and
detail images, and the scoped `request_log` text (the `initial` entry plus every
entry whose typed `targets` name this part, or absent typed targets every entry
matched by `log.py request search --query <part id or name>`). It SHALL NOT
receive the part script. The auditor answers the Visual Review Checklist
questions, each against a specific cited view, AND judges whether the render
satisfies the fed request wording as a second, advisory bar. An audit failure
re-enters that part's builder as a targeted `visual_mismatch` fix.

#### Scenario: Auditor input isolation
- **WHEN** the auditor agent is spawned for a part
- **THEN** its prompt contains the plan entry, the image paths, and the scoped
  `request_log` text but no part script source

#### Scenario: Audit failure
- **WHEN** the auditor answers any checklist question "no"
- **THEN** it names the question, the cited view, and the discrepancy, and the
  part's builder is resumed with that finding

#### Scenario: Request-conformance finding is advisory
- **WHEN** the auditor judges the render contradicts the fed request wording but
  every checklist question still answers "yes"
- **THEN** the audit verdict is `pass`, an advisory finding naming the contradicted
  request text and its cited view is returned in `findings`, and it is surfaced to
  the user without resuming the builder

#### Scenario: Request contradiction that also fails a checklist question
- **WHEN** the discrepancy that contradicts the request wording also answers a
  checklist question "no"
- **THEN** it is returned in `failed_questions` as `severity: blocking` with the
  request text cited as supporting evidence, and the builder is resumed

### Requirement: Planner runs as a strong-model agent
Phase 2 plan generation SHALL run in a sub-agent whose prompt is the rendered
`prompts/planning.md` and whose model is read from `skill_config.json`'s
`models.planner`, overridden per call; absent that file or key, the strongest
available model. The planner agent SHALL write `BUILD_PLAN.json` to the working
directory itself and run `plan.py validate` itself via Bash, retrying against its own
validation errors up to a bounded number of attempts (matching the builder agent's
3-attempt convention), before returning. The user approval checkpoint (`plan.py summary`
run against the file the agent wrote) remains in the main session.

#### Scenario: Plan validation loop stays inside the planner agent
- **WHEN** `plan.py validate` rejects the planner's first write of `BUILD_PLAN.json`
- **THEN** the planner agent itself reruns `plan.py validate` after fixing the plan,
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

### Requirement: Builder agents use the configured authoring model
A builder agent spawned for an autonomous part SHALL use the `model` field of
`render_prompt.py builder`'s JSON output (resolved from `skill_config.json`'s
`models.part_author`; absent that file or key, the documented mid-tier default) as its
per-call model override. The main session SHALL NOT re-read `skill_config.json`
itself to make this decision. When the value is `"inline"`, the part loop SHALL run in
the calling session instead of spawning a builder agent. The model actually used SHALL
be what Step 5's telemetry record names.

#### Scenario: Configured authoring model
- **WHEN** `models.part_author` names a model and a part routes autonomous
- **THEN** `render_prompt.py builder`'s JSON output carries that model in its `model`
  field, the builder agent is spawned with it, and its `attempts.jsonl` records name
  that model

#### Scenario: Inline authoring
- **WHEN** `models.part_author` is `"inline"`
- **THEN** `render_prompt.py builder`'s JSON output carries `"inline"` in its `model`
  field, no builder agent is spawned, and the part loop runs in the main session with
  telemetry naming the main session's model

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

### Requirement: Phase 0 sourcing search runs as a sourcing agent
When Phase 0 sourcing triage runs (not skipped by an explicit from-scratch request), the
search workflow (web search, Thingiverse, Printables, MakerWorld, GitHub lookups; opening
result pages and reading descriptions, comments, and licenses) SHALL run in a sourcing
agent whose prompt is the rendered `prompts/sourcing.md`. The agent SHALL return only a
structured candidate list (source URL, platform, kind, license, notes) to the main
session. The five-rung classification, license enforcement, and rung-3 user confirmation
SHALL remain in the main session.

#### Scenario: Heavy pages stay in the sourcing agent
- **WHEN** the sourcing agent opens model listing pages across Thingiverse, Printables,
  and MakerWorld
- **THEN** the main session receives the candidate list and sources, not page snapshots

#### Scenario: Classification stays in the main session
- **WHEN** the sourcing agent returns two candidates, one a parametric source and one a
  mesh
- **THEN** the main session (not the agent) applies the five-rung ladder and picks rung 1

### Requirement: Dimension lookup runs as a research agent
When Phase 1 requires real-world dimension lookups, the lookup workflow (web
search, spec pages, community model pages, STL download + `measure_stl.py`)
SHALL run in a research agent that returns only the dimension validation table
(value, source, status per row) and source URLs. When no lookup is needed, no
research agent is spawned. This is distinct from Phase 0's sourcing agent (see "Phase 0
sourcing search runs as a sourcing agent"): the research agent looks up dimensions of a
named real-world object, not whole reusable models.

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

