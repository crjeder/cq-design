# eval-harness Specification

## Purpose

Provide a repeatable benchmark for the pipeline: a canonical request corpus with golden meshes and
a runner that scores first-shot success, attempts-to-pass, Chamfer distance, and cost per accepted
part -- so prompt, reference, and model-routing changes are verified empirically instead of shipped
on vibes.

## Requirements

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

Correspondence between a produced mesh and a golden mesh SHALL be established
geometrically, not by part identifier. The runner SHALL enumerate a case's
produced solids from the export naming contract -- the STL files in the run's
`stl/` directory, excluding fused plate files (`plate_*.stl`) and keep-out zone
files (`keep_out__*.stl`) -- and SHALL solve a one-to-one assignment between
those solids and the case's golden meshes. The assignment cost SHALL be a shape
descriptor independent of Chamfer distance, so that the reported Chamfer is not
biased by having been minimized during pairing. Chamfer SHALL be computed only
for assigned pairs. The scorecard SHALL record which produced solid was
assigned to each golden part.

The scorecard SHALL report produced-versus-golden cardinality. A golden part
left unmatched SHALL be reported as a miss and SHALL cause the case's
`within_tolerance` to be false, rather than being excluded from the average. A
case whose run directory contains no produced solids SHALL be reported in a
state distinct from a case whose metrics are merely unavailable. Surplus
produced solids beyond the golden count SHALL be reported against the case's
expected part count.

The aggregate SHALL report how many cases contributed to the mean Chamfer
distance, so that a change in the contributing case set is visible rather than
appearing as a change in the metric.

#### Scenario: Chamfer distance against golden mesh
- **WHEN** a case's produced STL matches its golden mesh exactly
- **THEN** the reported Chamfer distance is at or near 0 mm and within the
  case's `tolerance_mm`

#### Scenario: Part identifiers need not agree
- **WHEN** a case's golden part is `sliding_lid` and the run produced
  `stl/lid.stl` with matching geometry
- **THEN** the two are assigned to each other and the reported Chamfer distance
  is at or near 0 mm, with the scorecard recording `lid` as the assigned solid

#### Scenario: Multi-union part is scored per union
- **WHEN** a run's `stl/` directory contains one STL per declared union rather
  than a single STL named after the part
- **THEN** those union STLs are enumerated as produced solids and assigned to
  golden meshes like any other

#### Scenario: Plate and keep-out files are not scored
- **WHEN** a run's `stl/` directory contains `plate_1.stl` and
  `keep_out__body__cavity.stl` alongside the per-union STLs
- **THEN** neither file is treated as a produced solid, and the per-union STLs
  alone are assigned to golden meshes

#### Scenario: Assignment is not chosen by minimizing the reported metric
- **WHEN** two produced solids could each be paired with either of two golden
  meshes
- **THEN** the pairing is selected using the Chamfer-independent shape
  descriptor, and Chamfer is computed only for the resulting pairs

#### Scenario: Unmatched golden part fails the case
- **WHEN** a case has two golden parts, the run produced one solid, and that
  solid matches its assigned golden mesh within tolerance
- **THEN** the unmatched golden part is reported as a miss and the case's
  `within_tolerance` is false

#### Scenario: Empty run directory is distinguishable from a scoring gap
- **WHEN** a case's run directory contains no produced solids
- **THEN** the case is reported in a no-artifacts state distinct from
  unavailable metrics, with `within_tolerance` false

#### Scenario: Aggregate exposes its coverage
- **WHEN** the mean Chamfer distance is aggregated over cases
- **THEN** the scorecard reports the number of cases that contributed to that
  mean

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
routing, and that the part loop (`skill/phase3_build.md`) append one telemetry
record per attempt via the telemetry helper.

#### Scenario: Part loop includes the telemetry step
- **WHEN** the skill's part loop (`skill/phase3_build.md`) is followed for one attempt
- **THEN** it directs appending one record to `build/attempts.jsonl` via
  `telemetry.py` as a mandatory loop step once the attempt's outcome (including
  any visual review) is decided
