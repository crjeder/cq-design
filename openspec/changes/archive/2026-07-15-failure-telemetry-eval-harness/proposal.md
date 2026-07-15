# Failure Telemetry + Eval Harness

## Why

The pipeline has no measurement: there is no record of where part attempts fail
(error types, attempt counts, review outcomes) and no repeatable benchmark, so
every prompt, reference, or model-routing change is unverifiable. This is the
prerequisite for tuning everything else in the improvement plan - archetype
templates, elicitation hooks, static lint, typed OCC triage, and per-phase model
routing all claim effects that only a baseline can confirm or refute.

## What Changes

- Every part attempt in the part loop appends one JSON line to
  `build/attempts.jsonl`: part id, attempt number, error types encountered,
  whether visual review failed and on which question, approximate prompt size,
  and the model that authored the attempt (a field that becomes meaningful once
  model routing lands).
- New `evals/` directory with ~10 canonical requests, each carrying a
  `BUILD_PLAN.json` and a golden mesh.
- New eval runner script that executes the canonical requests and scores:
  first-shot success rate, attempts-to-pass, Chamfer distance against the
  golden mesh, and cost per accepted part (tokens x model price x attempts).
- SKILL.md part loop gains a telemetry hook step (append one line per attempt)
  and a rule to run the eval suite before/after any prompt, reference, or
  model-routing change.

## Capabilities

### New Capabilities

- `attempt-telemetry`: append-only per-attempt JSONL log written from the part
  loop; schema of the attempt record; append semantics across sessions.
- `eval-harness`: canonical request corpus with golden meshes plus a runner
  that scores first-shot success, attempts-to-pass, Chamfer distance, and cost
  per accepted part.

### Modified Capabilities

<!-- none - existing spec requirements are unchanged; the part loop gains an
     additive logging step covered by attempt-telemetry -->

## Impact

- SKILL.md: part-loop step addition (telemetry append), eval-run rule.
- New files: `evals/` (requests + golden meshes + runner), telemetry helper if
  the append logic warrants one.
- `build/attempts.jsonl` becomes a session artifact alongside the existing
  `build/orientations.json`; it also feeds the resume-state work (improvement
  plan item 11) and reference condensation (item 14).
- No changes to the wrapper JSON contract or existing checks.
