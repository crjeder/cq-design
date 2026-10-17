# eval-harness Specification

## Purpose

Provide a repeatable benchmark for the pipeline: a canonical request corpus with golden meshes and
a runner that scores first-shot success, attempts-to-pass, Chamfer distance, and cost per accepted
part -- so prompt, reference, and model-routing changes are verified empirically instead of shipped
on vibes.
## Requirements
### Requirement: Canonical eval corpus
The repository SHALL contain an `evals/cases/` corpus of approximately 10-15
canonical requests. Each case directory SHALL contain the verbatim user
request (`request.md`), a golden `BUILD_PLAN.json` that passes
`plan.py validate`, one or more golden meshes under `golden/` in the authored
frame, and a `case.json` with at minimum `tolerance_mm` and the expected part
count.

The corpus SHALL include at least one case whose golden `BUILD_PLAN.json`
declares a `joints` entry (a matched-pair block such as `pin_hinge`) linking
two parts, a `kinematics` entry sweeping that joint's declared range, and a
shared-pivot interface referenced by both parts -- exercising multi-part
mate-chain-derived placement, not independently authored literals.

The corpus SHALL include at least one round-2 correction case: a case
directory containing a `seed/` subdirectory holding a prior round's accepted
`BUILD_PLAN.json` and part script(s), whose `request.md` is phrased as a
correction to that seeded state (not a from-scratch specification), and whose
golden reflects the corrected result.

The corpus SHALL include at least one case whose `request.md` names the same
feature using both a viewing-station phrase (e.g. "visible in the South
view") and a face-normal phrase (e.g. "on the East-facing wall"), such that
conflating the two would place the feature on the opposite side under the
`prompts/planning.md` fixed compass convention (North=+Y, East=+X).

#### Scenario: Case plans are valid
- **WHEN** `plan.py validate` is run against any case's `BUILD_PLAN.json`
- **THEN** validation passes with no errors

#### Scenario: Case is self-contained
- **WHEN** a case directory is inspected
- **THEN** it contains `request.md`, `BUILD_PLAN.json`, at least one golden
  mesh, and `case.json`

#### Scenario: Joints-and-kinematics case is present
- **WHEN** the corpus is inspected
- **THEN** at least one case's `BUILD_PLAN.json` has a non-empty `joints`
  array, a non-empty `kinematics` array, and two parts that reference a
  common interface fused by that joint

#### Scenario: Round-2 correction case is present
- **WHEN** the corpus is inspected
- **THEN** at least one case directory contains `seed/` with a prior-round
  `BUILD_PLAN.json` and part script, and that case's `request.md` reads as a
  correction to the seeded state

#### Scenario: Compass-wording case is present
- **WHEN** the corpus is inspected
- **THEN** at least one case's `request.md` refers to one feature by both a
  viewing-station phrase and a face-normal phrase for opposite compass
  directions, and its golden mesh places the feature per the fixed convention

The corpus MAY additionally contain cases imported from an external
text-to-CadQuery corpus via `evals/import_external_corpus.py` (see the
`external-corpus-import` capability). An imported case's `BUILD_PLAN.json` MAY be
a synthesized single-part plan (one `parts` entry, no `units`/`joints`/
`kinematics`) rather than hand-authored, but SHALL still pass `plan.py validate`
like any other case's plan. An imported case's `request.md` is the source
corpus's original pair description, not necessarily written in this skill's usual
conversational-request style. Imported cases are distinguished from hand-authored
ones by an `"external"` entry in `case.json`'s `tags` array, not by directory
location -- both live as flat siblings under `evals/cases/`.

#### Scenario: An imported case's plan is a synthesized single-part plan
- **WHEN** a case's `case.json` `tags` array includes `"external"`
- **THEN** its `BUILD_PLAN.json` contains exactly one `parts` entry and no
  `units`, `joints`, or `kinematics` fields, and still passes `plan.py validate`

### Requirement: Case subsetting by tag
The eval runner (`evals/run_evals.py`) SHALL support a `--tags` argument
(comma-separated). When given, a case SHALL be included only if its `case.json`
`tags` array intersects the given set; a case with no `tags` key SHALL be treated
as having an empty tag set. When `--tags` is omitted, case selection SHALL be
unaffected (all cases, or the `--cases` subset if given). When both `--cases` and
`--tags` are given, the effective case set SHALL be their intersection.

#### Scenario: Tag filter selects the external corpus only
- **WHEN** the runner is invoked with `--tags external`
- **THEN** only cases whose `case.json` `tags` array contains `"external"` are
  scored

#### Scenario: Tag filter selects the canonical corpus by exclusion
- **WHEN** the runner is invoked with `--tags canonical` and every hand-authored
  case's `case.json` includes a `"canonical"` tag
- **THEN** only hand-authored cases are scored

#### Scenario: No tag filter leaves existing behavior unchanged
- **WHEN** the runner is invoked without `--tags`
- **THEN** case selection behaves exactly as it did before this field existed

#### Scenario: Cases predating the tags field are excluded by any tag filter
- **WHEN** a case's `case.json` has no `tags` key and `--tags` is given
- **THEN** that case is excluded from the run (empty tag set does not intersect
  any non-empty filter)

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
cost per accepted part. The scorecard SHALL be emitted as JSON
and as human-readable markdown.

Before computing attempt- and cost-based metrics, the runner SHALL fold
`attempts.jsonl` with `log.py`'s `fold_attempts` (group by `(part_id,
attempt)`, keep the last record in file order), so a part-script attempt
represented by more than one line — a base record plus a later
visual-review follow-up — is scored once, using its authoritative
(last-written) `outcome`.

Cost per case SHALL be a billed token cost when one was recorded, and an
estimate otherwise. The runner SHALL prefer, in order: `<case>/cost.json` (the
`claude -p` result envelope captured at generation), then
`<case>/build/cost.json` (the session-cost record's `combined` total), then an
estimate computed from telemetry `prompt_chars` and the `src/model_prices.json`
price table (input rate only, tokens ~ `prompt_chars / 4`). The scorecard SHALL
record which source each case's cost came from. The `src/model_prices.json`
table SHALL provide an input and an output rate per model.

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
  sizes and no billed cost was recorded
- **THEN** its cost contribution sums the estimated token cost of all three
  attempts, not only the passing one

#### Scenario: Missing telemetry degrades, not crashes
- **WHEN** a run directory lacks `build/attempts.jsonl`
- **THEN** the runner still reports Chamfer metrics and marks attempt- and
  cost-based metrics as unavailable

#### Scenario: Recorded billed cost is preferred over the estimate
- **WHEN** a case run directory contains `cost.json` with a `total_cost_usd`
- **THEN** the scorecard uses that value for the case's cost and marks the
  case's cost source as recorded, not the `prompt_chars` estimate

#### Scenario: Estimate is used when nothing was recorded
- **WHEN** a case run directory has telemetry but neither `cost.json` nor
  `build/cost.json`
- **THEN** the scorecard falls back to the `prompt_chars` estimate and marks the
  case's cost source as an estimate

#### Scenario: A base-plus-follow-up attempt is counted once
- **WHEN** `attempts.jsonl` holds a base record for `part_id: "lid"`,
  `attempt: 1`, `outcome: "pass"` and a later follow-up record for the same
  `part_id`/`attempt` with `outcome: "fail"` (a visual-review mismatch)
- **THEN** `attempts_to_pass` and `first_shot_rate` treat this as one attempt
  with `outcome: "fail"` (the folded, last-written record), not as two
  attempts

### Requirement: Generation captures the result envelope
When `run_evals.py` generates a case (`--generate`), it SHALL invoke `claude -p`
with `--output-format json`, capture the result envelope, and write the case's
`session_id`, `num_turns`, `duration_ms`, `total_cost_usd`, and token `usage`
block to `<case>/cost.json`. A generation that times out or whose output cannot
be parsed SHALL leave `<case>/cost.json` unwritten rather than write a partial or
guessed record.

Before invoking `claude -p`, generation SHALL check the case directory for a
`seed/` subdirectory. When present, its contents SHALL be copied into the
case's working directory first, and the request prompt SHALL be framed as a
correction to that seeded state rather than a from-scratch request. When
`seed/` is absent, generation SHALL behave exactly as before: an empty working
directory and a from-scratch request.

#### Scenario: Envelope written on a successful generation
- **WHEN** a case is generated and `claude -p` returns a JSON result envelope
- **THEN** `<case>/cost.json` exists and contains `total_cost_usd` and the
  `usage` token counts from that envelope

#### Scenario: Timed-out generation writes no cost file
- **WHEN** a case generation times out
- **THEN** `<case>/cost.json` is not created, and scoring falls back to
  `build/cost.json` or the estimate

#### Scenario: Seeded case starts from a prior accepted state
- **WHEN** a case directory contains `seed/` with a `BUILD_PLAN.json` and part
  script, and generation runs with `--generate`
- **THEN** those files exist in the case's working directory before
  `claude -p` is invoked, and the prompt frames `request.md` as a correction

#### Scenario: Unseeded case is unaffected
- **WHEN** a case directory has no `seed/` subdirectory
- **THEN** generation starts in an empty working directory exactly as before
  this change

### Requirement: Eval discipline in the skill
SKILL.md SHALL instruct that the eval suite be run (score mode over a fresh or
prior generation) before and after any change to prompts, references, or model
routing, and that the part loop (`skill/phase3_build.md`) append one telemetry
record per attempt via the telemetry helper.

#### Scenario: Part loop includes the telemetry step
- **WHEN** the skill's part loop (`skill/phase3_build.md`) is followed for one attempt
- **THEN** it directs appending one record to `build/attempts.jsonl` via
  `log.py attempt` as a mandatory loop step once the attempt's outcome (including
  any visual review) is decided

