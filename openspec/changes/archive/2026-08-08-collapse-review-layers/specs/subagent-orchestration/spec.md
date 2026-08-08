## MODIFIED Requirements

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
