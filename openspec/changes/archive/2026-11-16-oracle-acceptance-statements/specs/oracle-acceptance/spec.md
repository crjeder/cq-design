## ADDED Requirements

### Requirement: The oracle derives statements from the intent without the plan

During Phase 1, after the dimension table is resolved and the reformulation is drafted,
the orchestrator SHALL write `build/oracle_request.md` containing the user's original
request, the draft reformulation (labelled as such), and the dimension table with each
row's planned `parameters.py` constant name. It SHALL render the oracle prompt with
`render_prompt.py oracle --request-file build/oracle_request.md` and spawn the
`cq-design-oracle` agent (fallback `cq-design:oracle`), passing the render output's
`agent_model`. The oracle's input SHALL NOT include `BUILD_PLAN.json` or any part of it,
and its prompt SHALL forbid reading it. The oracle SHALL write `acceptance.json` at the
project root, run `oracle.py validate` on it, retry against its own errors up to 3 times,
and return a status contract (`status`, `statements`, `attempts`, `error_summary`).

#### Scenario: First Phase 1 run

- **WHEN** the reformulation for a wall hook is drafted and no `BUILD_PLAN.json` exists
- **THEN** the oracle is spawned with only `build/oracle_request.md` in its rendered
  prompt and writes `acceptance.json` with statements `S1..Sn`

#### Scenario: Oracle prompt contains no plan

- **WHEN** `render_prompt.py oracle` is run in a project whose `BUILD_PLAN.json` exists
- **THEN** the rendered prompt contains no content from `BUILD_PLAN.json`

#### Scenario: Oracle exhausts its retries

- **WHEN** `oracle.py validate` still reports errors after the oracle's third attempt
- **THEN** the oracle returns `status: "blocked"` with `error_summary`, and the
  orchestrator shows the errors to the user before resuming the same oracle

### Requirement: acceptance.json uses a closed, frame-free statement vocabulary

`acceptance.json` SHALL be `{"schema_version": 1, "statements": [...]}`. Each statement
SHALL have a unique `id` matching `^S[1-9][0-9]*$`, a `kind`, a non-empty `cites` list, and
a non-empty plain-language `text`. `kind` SHALL be one of `part_count`, `feature`, `fit`,
`spacing`, `extent`, `probe`, `visual`, with the kind-specific fields the
`oracle.py` schema defines. No statement SHALL carry a coordinate, a point, or a direction
in the build frame. Numeric fields SHALL accept a number or an expression over
`parameters.py` names, evaluated with `plan_params.evaluate`. `tol_mm` SHALL default to
0.2.

#### Scenario: Coordinate rejected

- **WHEN** a `feature` statement includes a `position_mm` field
- **THEN** `oracle.py validate` reports a schema error naming the statement

#### Scenario: Expression over a parameter

- **WHEN** a `fit` statement has `accepts: {"diameter_mm": "HANDLE_DIAMETER_MM"}` and
  `parameters.py` defines `HANDLE_DIAMETER_MM = 24.0`
- **THEN** the checks use 24.0, and a later edit of that constant changes the checked value

#### Scenario: Unknown parameter name

- **WHEN** a numeric field references a name `parameters.py` does not define, at a time
  when `parameters.py` exists
- **THEN** `oracle.py validate` reports an error naming the statement and the name

### Requirement: Every statement cites the intent

Each entry of a statement's `cites` SHALL be either a substring of the approved `intent`
(compared after collapsing whitespace runs to one space) or a `parameters.py` constant
name. `oracle.py validate --intent <text>` and the plan-time check (against
`BUILD_PLAN.json`'s `intent`) SHALL report every statement with no matching citation as an
error. A requirement not in the intent SHALL enter only by correcting the intent and
re-running the oracle, never by editing `acceptance.json` by hand.

#### Scenario: Citation found

- **WHEN** a statement cites "two countersunk holes" and `intent` contains "screwed to the
  wall through two countersunk holes"
- **THEN** no citation error is reported

#### Scenario: Invented requirement

- **WHEN** a statement cites "dishwasher safe" and `intent` contains no such text
- **THEN** validation reports an uncited-statement error naming that statement

### Requirement: Statements a script cannot check are tagged visual

A requirement the oracle cannot express in the checkable kinds SHALL be emitted as
`kind: "visual"` with its `text`, and SHALL NOT be dropped. `visual` statements SHALL be
excluded from geometric verification and SHALL be fed to the part review as checklist
questions (see `request-relative-acceptance`).

#### Scenario: Aesthetic requirement

- **WHEN** the intent says "rounded, friendly look"
- **THEN** `acceptance.json` carries a `visual` statement citing that text

### Requirement: Statements are shown and approved at the Phase 1 exit checkpoint

The Phase 1 exit checkpoint SHALL include, as a fourth item after the concept sketch, the
oracle's statements as a numbered list of `id` and `text` (never raw JSON), with `visual`
statements marked as checked by review. Phase 1 SHALL NOT be approved while
`acceptance.json` is missing or fails `oracle.py validate`. When the user corrects a
statement, the orchestrator SHALL apply the correction to the reformulation, log it as a
`correction` entry, and resume the same oracle agent with the corrected reformulation.

#### Scenario: User approves

- **WHEN** the user approves the checkpoint showing statements S1-S6
- **THEN** `acceptance.json` stays as written and Phase 2 starts

#### Scenario: User corrects a statement

- **WHEN** the user replies "S4 is wrong, the lip only needs to be 5 mm"
- **THEN** the reformulation is amended, the correction is logged, the oracle is resumed,
  and the updated statements are shown again before approval

### Requirement: The plan binds every statement and contradictions fail validation

`BUILD_PLAN.json` SHALL accept an optional `acceptance_bindings` array of
`{statement, part, interfaces?, probes?}` objects. When `acceptance.json` exists next to
the plan, `plan.py validate` SHALL call `oracle.check` and report an error for each of:
a non-`part_count` statement with no binding; a binding to a statement id not in
`acceptance.json`; a bound `part`, interface name, or probe label that does not exist; a
bound entity whose attributes contradict the statement (wrong interface type family,
count, size outside `tol_mm`, spacing outside `tol_mm`, `dimensions` outside an `extent`
bound, `part_count` mismatch); and a `probe` statement with no bound probe whose label
starts with its id. Each error SHALL name the statement id and its `text`. When
`acceptance.json` is absent, no oracle check SHALL run.

#### Scenario: Dropped requirement

- **WHEN** `acceptance.json` has `S3` spacing "holes 156 mm apart" and the plan has no
  binding for `S3`
- **THEN** `plan.py validate` fails with an error naming `S3` and its text

#### Scenario: Contradicting binding

- **WHEN** `S3` is bound to two interfaces whose `position_mm` are 120 mm apart
- **THEN** validation fails naming `S3`, the expected 156 mm, and the found 120 mm

#### Scenario: No acceptance file

- **WHEN** a plan from the eval corpus is validated with no `acceptance.json` beside it
- **THEN** no oracle errors are reported and `acceptance_bindings` is not required

### Requirement: The planner corrects binding errors and blocks after 3 attempts

The planner prompt SHALL instruct the planner to read `acceptance.json` and write
`acceptance_bindings` for every statement. Oracle binding errors SHALL be handled by the
planner's existing self-retry against `plan.py validate`. After 3 attempts with oracle
errors remaining, the planner SHALL return `status: "blocked"`, and the orchestrator SHALL
show the failing statements to the user rather than spawning a second planner.

#### Scenario: Planner fixes a missing binding

- **WHEN** the planner's first `plan.py validate` reports `S3` unbound
- **THEN** it adds the interfaces and the binding and re-validates within the same run

#### Scenario: Planner cannot satisfy a statement

- **WHEN** three attempts all still report `S5` contradicted
- **THEN** the planner returns `blocked` with `S5` in `error_summary`

### Requirement: Built geometry is verified against bound statements

The quality gate SHALL run an `oracle` stage when `acceptance.json` exists. For each
bound, non-`visual` statement on the gated part, `oracle.verify` SHALL check: for
`feature`, `fit`, and `spacing`, that the bound interfaces have no feature-presence
failure; for `extent`, the sorted extents of the part's BRep bounding box in build pose
against the bound; for `probe`, each bound probe evaluated on the final body with
`probes.py`. Each unmet statement SHALL produce an issue `{"source": "oracle",
"severity": "error", "type": "oracle_unmet", "statement": <id>, "message", "hint",
"round"}`.

#### Scenario: Extent exceeded

- **WHEN** `S2` says the largest extent is at most 120 mm and the built part's largest
  bbox extent is 131 mm
- **THEN** the gate emits `oracle_unmet` for `S2` with both values in the message

#### Scenario: Probe statement met

- **WHEN** `S6` is bound to a probe `S6: lip blocks lift-out` that passes on the final body
- **THEN** no oracle issue is emitted for `S6`

### Requirement: Oracle findings go to the builder for 3 rounds, then escalate

`round` SHALL be 1 for a statement not failing in the `--previous` report, and the prior
round plus 1 when it is. An `oracle_unmet` issue with `round` below 3 SHALL carry action
`fix` and go to the part's builder as a correction naming the statement `text`. When
`round` reaches 3, the action SHALL be `ask_user` (the gate's existing ask-the-user action). The orchestrator SHALL then stop
resuming the builder for that statement and ask the user to amend the intent (which
re-runs the oracle), accept as-is, or skip the part. This cap is separate from the gate's
`fix`-round cap.

#### Scenario: Second round

- **WHEN** `S2` failed in the prior report with `round: 1` and still fails
- **THEN** the new issue has `round: 2` and action `fix`

#### Scenario: Third round escalates

- **WHEN** `S2` failed with `round: 2` and fails again
- **THEN** the issue has `round: 3` and action `ask_user`, and no further builder
  correction is sent for `S2`

### Requirement: acceptance_ts records reconciliation and staleness fails validation

`BUILD_PLAN.json` SHALL accept an optional ISO-8601 UTC `acceptance_ts`. When
`acceptance.json` exists, `plan.py validate` SHALL report an error when any
`clarification` or `correction` entry in `request_log` has a `ts` newer than
`acceptance_ts`, or when such an entry exists and `acceptance_ts` is absent, naming the
unreconciled entries. An unparseable value SHALL be reported as an error. `log.py request
add` SHALL accept `--acceptance-reconciled`, which sets `acceptance_ts` to the appended
entry's `ts`. Phase 2 SHALL write `acceptance_ts` with the plan, set to the same value as
`intent_ts`, or to the `initial` entry's `ts` when there is no `intent_ts`. On a
mid-build correction, the orchestrator SHALL resume the oracle with the correction, show
any changed statements to the user, and then record reconciliation, advancing the stamp
even when no statement changed.

#### Scenario: Correction not reconciled

- **WHEN** a `correction` entry is newer than `acceptance_ts`
- **THEN** `plan.py validate` fails naming that entry, and the gate reports `plan_invalid`

#### Scenario: Correction reconciled

- **WHEN** the oracle is re-run after a correction and `log.py request add ...
  --acceptance-reconciled` is used
- **THEN** `acceptance_ts` equals the entry's `ts` and validation reports no staleness

### Requirement: The plan summary shows statement bindings

When `acceptance.json` exists, `plan.py summary` SHALL include an **Acceptance** section
listing each statement's `id`, `text`, and the part plus interfaces or probes it is bound
to, with `visual` statements labelled as checked by review.

#### Scenario: Summary at the plan checkpoint

- **WHEN** `plan.py summary` runs on a plan binding `S3` to `plate.hole_a, plate.hole_b`
- **THEN** the output's Acceptance section lists `S3`, its text, and those two interfaces
