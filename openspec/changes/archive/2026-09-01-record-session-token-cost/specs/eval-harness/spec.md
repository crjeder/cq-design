## MODIFIED Requirements

### Requirement: Eval metrics
The scorecard SHALL report, per case and aggregated: first-shot success rate
(fraction of parts whose first attempt passed), mean attempts-to-pass,
symmetric Chamfer distance in mm between each produced mesh and its golden
mesh (both meshes centered by bounding-box center; no rotation solving), and
cost per accepted part.

Cost per case SHALL be a billed token cost when one was recorded, and an
estimate otherwise. The runner SHALL prefer, in order: `<case>/cost.json` (the
`claude -p` result envelope captured at generation), then
`<case>/build/cost.json` (the session-cost record's `combined` total), then an
estimate computed from telemetry `prompt_chars` and the `evals/model_prices.json`
price table (input rate only, tokens ~ `prompt_chars / 4`). The scorecard SHALL
record which source each case's cost came from. The `evals/model_prices.json`
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

## ADDED Requirements

### Requirement: Generation captures the result envelope
When `run_evals.py` generates a case (`--generate`), it SHALL invoke `claude -p`
with `--output-format json`, capture the result envelope, and write the case's
`session_id`, `num_turns`, `duration_ms`, `total_cost_usd`, and token `usage`
block to `<case>/cost.json`. A generation that times out or whose output cannot
be parsed SHALL leave `<case>/cost.json` unwritten rather than write a partial or
guessed record.

#### Scenario: Envelope written on a successful generation
- **WHEN** a case is generated and `claude -p` returns a JSON result envelope
- **THEN** `<case>/cost.json` exists and contains `total_cost_usd` and the
  `usage` token counts from that envelope

#### Scenario: Timed-out generation writes no cost file
- **WHEN** a case generation times out
- **THEN** `<case>/cost.json` is not created, and scoring falls back to
  `build/cost.json` or the estimate
