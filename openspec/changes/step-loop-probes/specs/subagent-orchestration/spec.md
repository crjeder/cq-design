## MODIFIED Requirements

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

### Requirement: Blocked escalation resumes the same agent
When a step report sets `probe_stuck: true`, or the part needs a block or primitive the
inventory does not provide, the builder SHALL return `blocked` with reason
`probe_stuck` or `missing_block` and an error summary naming the probe or the missing
geometry; the main session SHALL ask the user (plan change, hint, accept as-is, or
skip); on a plan change or a hint, the SAME builder agent SHALL be resumed rather than a
new agent spawned.

#### Scenario: Hint after a stuck probe
- **WHEN** the user provides a hint for a part blocked with `probe_stuck`
- **THEN** the original builder agent is resumed with the hint and its step history
  intact

#### Scenario: Plan change after a stuck probe
- **WHEN** the user changes the plan entry the stuck probe came from
- **THEN** the change is logged in `request_log`, the attempt count for that part
  increases by one, and the same builder is resumed
