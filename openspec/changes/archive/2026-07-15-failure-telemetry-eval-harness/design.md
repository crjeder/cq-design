# Design: Failure Telemetry + Eval Harness

## Context

The cq-design pipeline is driven inline by the orchestrating Claude: it reads
`BUILD_PLAN.json`, authors part scripts, runs `run_cadquery_model.py`, and
iterates on the typed errors in the JSON contract. Nothing records how many
attempts a part took, which error types recurred, or which visual-review
question failed - so there is no baseline against which prompt, reference, or
model-routing changes can be judged. `build/orientations.json` already
establishes the pattern of durable per-model state under `build/`.

## Goals / Non-Goals

**Goals:**

- One append-only JSONL record per part attempt, cheap enough to never skip.
- A repeatable eval corpus (~10 canonical requests with golden meshes) and a
  runner that scores first-shot success rate, attempts-to-pass, Chamfer
  distance, and cost per accepted part.
- Scoring must work over an existing run directory without re-invoking any
  model (score-only mode), so analysis is free even when generation is not.

**Non-Goals:**

- No dashboards, aggregation service, or CI wiring.
- No automatic regression gating - the runner reports scores; humans compare.
- No changes to the wrapper JSON contract, checks, or the quality gate.
- Model routing itself (improvement plan item 15) - telemetry only reserves a
  `model` field for it.

## Decisions

### D1: Single writer - Claude appends via a `src/telemetry.py` CLI

The wrapper knows error types but not attempt numbers, review outcomes, or
prompt sizes; only the orchestrating Claude sees all of them. So the part loop
(SKILL.md) appends the record, but through a small helper -
`python src/telemetry.py append build/attempts.jsonl '<json>'` (or `--field
k=v` flags) - rather than hand-writing JSONL in Bash. The helper validates the
record against the schema, stamps `ts`, and guarantees one well-formed line per
call.

- *Alternative considered*: auto-log inside `run_cadquery_model.py`. Rejected:
  the wrapper sees only its own run, would double-log with a Claude-side hook,
  and cannot record review outcomes or prompt size.
- *Alternative considered*: raw `echo >> attempts.jsonl` in SKILL.md. Rejected:
  quoting/JSON-escaping in PowerShell vs bash is exactly the kind of thing that
  silently corrupts an append-only log.

### D2: Attempt record schema

One JSON object per line:

```json
{
  "ts": "2026-07-15T12:00:00Z",
  "part_id": "housing",
  "attempt": 2,
  "outcome": "fail",
  "error_types": ["silent_boolean", "thin_interface"],
  "visual_review": {"passed": false, "failed_question": "Q3"},
  "prompt_chars": 41250,
  "model": "inline"
}
```

`outcome` is `pass` | `fail`. `visual_review` is null when review did not run
for that attempt. `prompt_chars` is the approximate rendered part-prompt size
(characters; tokens are estimated downstream as chars/4). `model` defaults to
`"inline"` until per-phase routing (item 15) supplies real model names.
Unknown extra keys are allowed - the schema is a floor, not a ceiling.

### D3: Eval corpus layout

```
evals/
  cases/<case-name>/
    request.md         # the verbatim user request
    BUILD_PLAN.json    # golden plan (validated by plan_validate)
    golden/*.stl       # golden mesh(es), authored frame
    case.json          # metadata: tags, tolerance_mm, expected part count
  run_evals.py         # runner + scorer
```

~10 cases spanning the archetypes the plan cares about (enclosure, lid,
bracket, adapter ring, clip, etc.). Golden meshes live in the authored frame so
Chamfer comparison needs no pose solving.

### D4: Runner is score-first; generation is external

`run_evals.py` scores a completed run directory: it reads
`build/attempts.jsonl` and produced STLs from a per-case output dir and emits a
JSON + markdown scorecard. Generation (actually running the skill against each
`request.md`) is done by invoking `claude -p` per case behind an explicit
`--generate` flag, because it costs real tokens and minutes; the default
invocation never spends money.

- *Alternative considered*: runner always generates. Rejected: makes the cheap
  half (re-scoring after a scoring tweak, comparing two existing runs)
  needlessly expensive and slow.

### D5: Metrics

- **first_shot_rate**: fraction of parts whose attempt 1 has `outcome: pass`.
- **attempts_to_pass**: mean attempts until first `pass` per part (failed
  parts count as attempts + 1, flagged).
- **chamfer_mm**: symmetric Chamfer distance between produced and golden mesh -
  sample N surface points on each (trimesh) and measure each sample against
  the OTHER mesh's surface (`trimesh.proximity.closest_point`, which needs the
  `rtree` dependency), mean of both directions. Point-to-surface rather than
  point-to-point so identical geometry scores 0 regardless of sampling
  density. Meshes are compared after centering both bounding-box centers at
  the origin; no rotation solving.
- **cost_per_accepted_part**: sum over attempts of
  `(prompt_chars / 4) * price(model)` divided by accepted parts. Prices come
  from a small `evals/model_prices.json` so they are editable data, not code.

### D6: SKILL.md hooks are minimal

Two additions: a part-loop step "after each attempt, append a telemetry record
via `telemetry.py`", and a rule "run `evals/run_evals.py` (score mode) before
and after changing prompts, references, or model routing". No phase
restructuring.

## Risks / Trade-offs

- [Eval generation cost: ~10 full skill runs per comparison] -> `--generate`
  is opt-in, supports `--cases a,b` subsetting, and score-only mode is free.
- [Chamfer without rotation alignment penalizes correct-but-reoriented parts]
  -> golden meshes are stored in the authored frame and cases pin the plan, so
  orientation is determined; `tolerance_mm` in `case.json` absorbs residual
  noise. Full registration (ICP) is explicitly out of scope.
- [Claude forgets to append telemetry mid-loop] -> the append is a single
  fixed command, its own numbered part-loop step (step 5, after the decide
  step so the record carries the review outcome); missing lines degrade
  metrics but corrupt nothing (append-only).
- [Token estimate chars/4 is crude] -> fine for A/B deltas on the same
  harness; absolute cost figures are labeled as estimates in the scorecard.

## Open Questions

- Which 10 requests make the corpus? Seed from the archetype list in
  improvement-plan item 2; finalize during implementation.
- Whether `claude -p` generation should run inside a temp working directory
  per case (likely yes, mirroring the skill's normal project scaffolding).
