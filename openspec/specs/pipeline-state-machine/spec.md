# Pipeline State Machine

## Purpose

TBD - Defines `src/pipeline.py`, which derives the build state from the journal and artifacts, reports allowed next steps, and refuses invalid milestone transitions.
## Requirements
### Requirement: Build state is derived from the journal and artifacts

The system SHALL provide `src/pipeline.py`, a stdlib-only script (no CadQuery import) whose `status` subcommand computes the build state on every call from `build/journal.md` and the on-disk artifacts. It SHALL NOT read or write a separate state file. Only journal lines after the last `phase0/restart` line SHALL count.

`status` SHALL print JSON with `route`, `done`, `void`, `stale_parts`, `allowed_next`, `blocked` (each entry naming the step and its unmet prerequisites) and `complete`.

#### Scenario: Fresh directory
- **WHEN** `pipeline.py status` runs in a directory with no `build/journal.md` on the `design` route
- **THEN** `done` is empty and `allowed_next` lists the first steps (`phase0/rung_decision`, `phase1/dimensions_approved`)

#### Scenario: Restart voids earlier lines
- **WHEN** the journal contains `phase1/dimensions_approved` followed by `phase0/restart`
- **THEN** `done` does not contain `phase1/dimensions_approved`

#### Scenario: No state file
- **WHEN** `status` runs
- **THEN** no file is created or modified

### Requirement: A milestone is valid only after its prerequisites

A journal line SHALL count as done only when, in the current attempt, the latest occurrence of every prerequisite milestone appears earlier in the journal than that line. A line failing this SHALL be reported under `void` with the unmet prerequisite, and SHALL NOT appear in `done` or satisfy a later milestone. The prerequisite table SHALL be: `plan_written` needs `dimensions_approved`; `plan_approved` needs `plan_written`; `part_accepted:<id>` needs `plan_approved`; `design_approved` needs `part_accepted:<id>` for every part id in `BUILD_PLAN.json`; `orientation_chosen` needs `design_approved`; `assembly_written` needs `orientation_chosen`; `gate_result` needs `assembly_written`; `delivered` needs `gate_result`.

#### Scenario: Dimensions re-approved after plan approval
- **WHEN** the journal has `dimensions_approved`, `plan_written`, `plan_approved`, then a second `dimensions_approved`
- **THEN** `plan_written` and `plan_approved` are listed under `void`, and `allowed_next` contains `phase2/plan_written`

#### Scenario: Design approval needs every part
- **WHEN** `BUILD_PLAN.json` has parts `lid` and `base` and only `part_accepted:lid` is recorded
- **THEN** `design_approved` is listed under `blocked` with `part_accepted:base` as the unmet prerequisite

#### Scenario: Script-written line out of order
- **WHEN** `plan.py validate` appended `plan_written` but no `dimensions_approved` precedes it
- **THEN** `plan_written` is reported under `void`

### Requirement: A changed part script voids its acceptance

A `part_accepted:<id>` line SHALL carry `sha=<script_hash>` of `build/<id>.py` in its text. `status` SHALL recompute the hash; a mismatch SHALL list the part under `stale_parts`, exclude it from `done`, and block `design_approved`. A line without `sha=` SHALL be treated as accepted with a warning, never as stale.

#### Scenario: Script edited after acceptance
- **WHEN** `build/lid.py` changes after `part_accepted:lid sha=<old hash>` was journalled
- **THEN** `lid` is in `stale_parts` and `allowed_next` includes the part loop for `lid`

#### Scenario: Legacy journal line
- **WHEN** a `part_accepted:lid` line has no `sha=`
- **THEN** `lid` is accepted and `status` emits a warning that it is unverified

### Requirement: Invalid transitions are refused before writing

`pipeline.py advance <milestone> <text>` SHALL check the milestone's prerequisites and route, then append the journal line through the existing journal appender. On refusal it SHALL write nothing, exit 1, and emit `errors` entries with `type`, `message`, `hint`, using the types `prerequisite_missing`, `route_forbids`, `unknown_milestone` and `part_stale`. `pipeline.py can <milestone>` SHALL perform the same check without writing and exit 1 when the milestone is not allowed.

#### Scenario: Out-of-order advance
- **WHEN** `advance phase3/orientation_chosen "..."` runs before `design_approved`
- **THEN** exit code is 1, `errors[0].type` is `prerequisite_missing`, and the journal is unchanged

#### Scenario: Valid advance
- **WHEN** `advance phase2/plan_approved "user approved"` runs with `plan_written` already recorded
- **THEN** the line `- phase2/plan_approved: user approved` is appended and exit code is 0

#### Scenario: Unknown milestone
- **WHEN** `advance phase9/foo "x"` runs
- **THEN** `errors[0].type` is `unknown_milestone` and nothing is written

### Requirement: Edit is an explicit plan-less route

`pipeline.py status --route edit` SHALL report the fixed edit steps without reading `BUILD_PLAN.json`, `build/` or the journal, and the absence of any of them SHALL NOT be an error. On the `edit` route, `advance` and `can` SHALL refuse plan, journal, `print_orientation` and `quality_gate` milestones with `route_forbids`. The route SHALL never be inferred; the caller supplies it.

#### Scenario: Edit with nothing on disk
- **WHEN** `status --route edit` runs in an empty directory
- **THEN** exit code is 0 and `allowed_next` lists the edit steps

#### Scenario: Gate refused on edit
- **WHEN** `can phase3/gate_result --route edit` runs
- **THEN** exit code is 1 with `errors[0].type` `route_forbids`

### Requirement: The plan route ends at plan approval

On the `plan` route `status` SHALL report `complete: true` once `phase2/plan_approved` is done and SHALL list no Phase 3 or Phase 4 step in `allowed_next`. The journal MAY later be continued on the `design` route.

#### Scenario: Plan-only run finished
- **WHEN** `plan_approved` is done and `--route plan` is given
- **THEN** `complete` is true and `allowed_next` is empty

#### Scenario: Plan run continued as design
- **WHEN** `plan_approved` is done and `--route design` is given
- **THEN** `complete` is false and `allowed_next` lists the part loop for each part without an accepted script

### Requirement: Sub-agent scope comes from the state

The builder prompt rendered by `render_prompt.py` SHALL state the part id and the steps `pipeline.py status` allows for that part, and SHALL tell the builder not to run steps beyond them.

#### Scenario: Builder prompt scope line
- **WHEN** the builder prompt is rendered for part `lid` with `plan_approved` done
- **THEN** it contains the allowed steps for `lid` and no step from Phase 3's export or later

### Requirement: Sourcing has its own status

`status` SHALL report `sourcing` as `pending` (no sourcing line), `skipped` (a `phase0/sourcing_skipped` line), or `rung_<n>` (the integer after `rung ` at the start of the `phase0/rung_decision` text). Sourcing SHALL NOT block Phase 1. For `rung_3` (mesh delivered as-is) `phase4/delivered` SHALL need only `rung_decision`, and Phases 1-3 SHALL be reported `skipped`. A `rung_decision` line without `rung <n>` SHALL be void.

#### Scenario: Triage skipped
- **WHEN** the journal has `phase0/sourcing_skipped`
- **THEN** `sourcing` is `skipped` and `phase1/dimensions_approved` is in `allowed_next`

#### Scenario: Rung 5 continues
- **WHEN** the journal has `phase0/rung_decision: rung 5, source none, license n/a`
- **THEN** `sourcing` is `rung_5` and the normal Phase 1 steps are allowed

#### Scenario: Rung 3 delivers as-is
- **WHEN** the journal has `rung 3` in `rung_decision`
- **THEN** `sourcing` is `rung_3`, Phases 1-3 are `skipped`, and `phase4/delivered` is in `allowed_next`

#### Scenario: Malformed rung line
- **WHEN** a `rung_decision` line has no `rung <n>`
- **THEN** it is listed under `void` and `sourcing` stays `pending`
