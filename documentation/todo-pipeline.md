# Pipeline enforcement -- details

Tasks: [TODO.md](../TODO.md#1-pipeline-enforcement-and-process-hygiene).

### Pipeline state machine


The pipeline order is enforced only by `SKILL.md` and `skill/phase*.md`; Claude
drives it inline and there is no orchestrator program. Recurring defects are
process drift, not geometry: sub-agents re-planning into downstream steps,
hooks not seeing sub-agent tool calls, resume trusting stale milestones (PR #250).

A small program (e.g. `src/pipeline.py`) reads the build state (plan, milestones,
attempt logs), reports the allowed next step(s), and rejects a transition whose
preconditions are not met. Claude still authors parts and runs user checkpoints;
sequencing, resume and sub-agent scope become checkable instead of instructed.
Resume, the telemetry hook and the builder's scope limit then read one source of truth.

`cq-design:edit` is a legitimate plan-less route (no `BUILD_PLAN.json`, no `build/`).
The state machine must model it explicitly, not reject it for a missing plan.

### LLM skipped the pipeline on an edit run

LLM didn’t follow the full cq-design pipeline. Its working folder has no BUILD_PLAN.json and no build/: just a part.py and two STEP files in out/ (model.step and part.step). The editing run seems to have taken a shortcut. It may need a prompt change if you want editing tasks to go through the real skill.
fix: let the program own the pipeline not the llm. exeption for edits.
Low priority, superseded by the [pipeline state machine](#pipeline-state-machine). Only seen in the benchmark edit tasks. Unchecked: whether those runs invoke `cq-design:edit` at all; if not, it is a harness issue, not a skill defect.

### Process hygiene and install checks

From the text-to-cad survey (2026-10-16; scripts and limit tables not read -- check the source before adopting).

Process hygiene (from their `AGENTS.md`): every test file reached by CI, flaky tests fixed or deleted never retried, no one-off helper scripts in `src/`

`init` / `status`: detect plugin + standalone skill both installed (duplicates every skill)
