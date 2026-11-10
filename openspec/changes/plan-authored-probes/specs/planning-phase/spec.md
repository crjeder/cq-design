## ADDED Requirements

### Requirement: Build plan carries optional per-part authored probes
Each part object MAY carry `probes`, an array of authored probe entries in the part's
build pose. Each entry SHALL require `kind` (one of `solid_at`, `empty_at`, `ray`,
`bbox`) and `label` (non-empty string naming the request or plan fact it checks), and
SHALL carry the fields its kind needs: `p` (`[x, y, z]`) for `solid_at`/`empty_at`;
`p`, `dir` (`[x, y, z]`) and `hits` (integer >= 0), with optional `length` (> 0), for
`ray`; `lo` and `hi` or `size` (each `[x, y, z]`), with optional `tol` (>= 0) and `mode`
(`exact` or `within`), for `bbox`. An entry MAY carry `instance`, which SHALL name a
`blocks_needed` instance id of the same part. The schema SHALL reject unknown fields
and the step-only kind `delta`.

#### Scenario: Plan with authored probes validates
- **WHEN** a part declares an `empty_at` probe with `p` and `label`, and a `ray` probe with `p`, `dir`, `hits` and `label`
- **THEN** `plan.py validate` passes

#### Scenario: Plan without probes still validates
- **WHEN** a part declares no `probes` field
- **THEN** validation passes

#### Scenario: Probe missing its label is rejected
- **WHEN** an authored probe has no `label`
- **THEN** validation fails with a schema error naming the probe

#### Scenario: Probe missing a kind field is rejected
- **WHEN** a `ray` probe omits `hits`
- **THEN** validation fails with a schema error

#### Scenario: Step-only kind is rejected
- **WHEN** an authored probe declares `kind: "delta"`
- **THEN** validation fails

#### Scenario: Probe instance must be planned
- **WHEN** an authored probe declares `instance: "lid_hinge"` and the part has no `blocks_needed` instance with that id
- **THEN** `plan.py validate` fails naming the part and the unknown instance

### Requirement: Planner turns unprobed request dimensions into authored probes
The planning prompt SHALL instruct the planner that every request dimension locating or
sizing a feature, which no `interfaces[]` entry with `position_mm` and a size already
covers, becomes one or more authored probes whose `label` quotes the request. A wall
thickness or step height SHALL be expressed as a `solid_at` point just inside the
surface and an `empty_at` point just past it.

#### Scenario: Prompt carries the probe rule
- **WHEN** the planning prompt is rendered
- **THEN** it contains the authored-probe rule and an example of a bracketing `solid_at`/`empty_at` pair
