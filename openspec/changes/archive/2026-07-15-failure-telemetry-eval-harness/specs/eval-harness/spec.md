# eval-harness

## ADDED Requirements

### Requirement: Canonical eval corpus
The repository SHALL contain an `evals/cases/` corpus of approximately 10
canonical requests. Each case directory SHALL contain the verbatim user
request (`request.md`), a golden `BUILD_PLAN.json` that passes
`plan_validate.py`, one or more golden meshes under `golden/` in the authored
frame, and a `case.json` with at minimum `tolerance_mm` and the expected part
count.

#### Scenario: Case plans are valid
- **WHEN** `plan_validate.py` is run against any case's `BUILD_PLAN.json`
- **THEN** validation passes with no errors

#### Scenario: Case is self-contained
- **WHEN** a case directory is inspected
- **THEN** it contains `request.md`, `BUILD_PLAN.json`, at least one golden
  mesh, and `case.json`

### Requirement: Score-only eval runs
The eval runner (`evals/run_evals.py`) SHALL, by default, score an existing
run directory without invoking any model: it reads that run's
`build/attempts.jsonl` and produced STLs and emits a scorecard. Generation
SHALL only occur behind an explicit `--generate` flag, and case subsetting
SHALL be supported via `--cases`.

#### Scenario: Default invocation spends no tokens
- **WHEN** the runner is invoked on a completed run directory without
  `--generate`
- **THEN** a scorecard is produced and no model invocation occurs

#### Scenario: Subset generation
- **WHEN** the runner is invoked with `--generate --cases enclosure,bracket`
- **THEN** only those two cases are generated and scored

### Requirement: Eval metrics
The scorecard SHALL report, per case and aggregated: first-shot success rate
(fraction of parts whose first attempt passed), mean attempts-to-pass,
symmetric Chamfer distance in mm between each produced mesh and its golden
mesh (both meshes centered by bounding-box center; no rotation solving), and
estimated cost per accepted part computed from telemetry `prompt_chars` and a
`evals/model_prices.json` price table. The scorecard SHALL be emitted as JSON
and as human-readable markdown.

#### Scenario: Chamfer distance against golden mesh
- **WHEN** a case's produced STL matches its golden mesh exactly
- **THEN** the reported Chamfer distance is at or near 0 mm and within the
  case's `tolerance_mm`

#### Scenario: Cost aggregates over all attempts
- **WHEN** a part passed on attempt 3 with telemetry recording three prompt
  sizes
- **THEN** its cost contribution sums the estimated token cost of all three
  attempts, not only the passing one

#### Scenario: Missing telemetry degrades, not crashes
- **WHEN** a run directory lacks `build/attempts.jsonl`
- **THEN** the runner still reports Chamfer metrics and marks attempt- and
  cost-based metrics as unavailable

### Requirement: Eval discipline in the skill
SKILL.md SHALL instruct that the eval suite be run (score mode over a fresh or
prior generation) before and after any change to prompts, references, or model
routing, and that the part loop append one telemetry record per attempt via
the telemetry helper.

#### Scenario: Part loop includes the telemetry step
- **WHEN** SKILL.md's part loop is followed for one attempt
- **THEN** it directs appending one record to `build/attempts.jsonl` via
  `telemetry.py` as a mandatory loop step once the attempt's outcome (including
  any visual review) is decided
