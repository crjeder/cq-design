# Approved Intent

## Purpose

Defines `BUILD_PLAN.json`'s `intent` field as the user-approved reformulation of the
request: what Phase 1 writes at its exit checkpoint once the user approves or corrects
it, how it differs from `request_log`'s verbatim `initial` entry, and when it must be
rewritten.

## Requirements

### Requirement: Phase 1 writes a user-approved reformulation into `intent`

At the Phase 1 exit checkpoint, the skill SHALL present a reformulation of the user's
request in resolved terms and, once the user approves or corrects it, SHALL write the
approved text into `BUILD_PLAN.json`'s `intent`. The reformulation SHALL state what is
being built and why, the confirmed reading of any shape the request left ambiguous, the
fit type of every mating surface, every assumption Phase 1 made rather than asked about
(each with its concrete assumed value), and the repo-relative `sketches/` path of every
user-supplied image the design is based on. It SHALL NOT restate values that a structured
field already carries in full (the dimension table lives in `parameters.py` and
`parts[].dimensions`; printer/material/nozzle live in the plan's own fields).

`request_log`'s `initial` entry keeps the user's original wording verbatim; `intent`
carries the resolved reading. Together they are the record of what was asked and what was
approved.

#### Scenario: Vague request is reformulated and approved

- **WHEN** the user opens with "a stand for my laptop" and Phase 1 resolves the machine
  model, the rake angle, the two-part decomposition, and a sliding fit
- **THEN** the exit checkpoint presents a reformulation naming all four, and on approval
  that text is written to `intent` while `request_log[0].text` still reads "a stand for
  my laptop"

#### Scenario: User corrects the reformulation

- **WHEN** the user replies to the checkpoint that the rake should be adjustable, not
  fixed
- **THEN** the corrected reading is written to `intent`, and the correction is appended to
  `request_log` as a `clarification` entry with its own `level` and `targets`

#### Scenario: Structured values are not restated

- **WHEN** the reformulation is written for a design with twelve looked-up dimensions
- **THEN** `intent` names the design in prose and does not reproduce the dimension table,
  which `parameters.py` already carries

### Requirement: Rebuild-cost ambiguity is asked; parameter ambiguity may be assumed

Phase 1 SHALL NOT proceed past its exit checkpoint while an unresolved ambiguity would, if
guessed wrong, cost a rebuild -- whether a part exists at all, what a part's overall shape
is, how two parts join, or which fit type a mating surface takes. Such ambiguity SHALL be
resolved by asking the user.

An ambiguity that is parameter-level -- a dimension or literal with the design otherwise
fixed -- MAY instead be resolved by assumption: the skill picks a concrete value, records
it in the approved reformulation as an explicit assumption, and lets the approval
checkpoint be where a wrong assumption is caught. No dimension SHALL leave Phase 1 as
`-1`.

#### Scenario: Joint type is unresolved

- **WHEN** the request does not say whether two parts screw together or snap together
- **THEN** Phase 1 asks the user rather than assuming, because the wrong choice rebuilds
  both parts

#### Scenario: Leg length is unresolved

- **WHEN** the request does not state how long the legs should be and no lookup supplies
  it
- **THEN** Phase 1 picks a concrete starting value, records it in the reformulation as an
  assumption ("legs 24 mm to start -- assumed, adjust after a test fit"), and does not
  block on a question

#### Scenario: A dimension could not be sourced

- **WHEN** a looked-up dimension is still `-1` when the exit checkpoint is prepared
- **THEN** the checkpoint asks the user for the value or for permission to assume one, and
  approval is not accepted while the `-1` stands

### Requirement: `intent` describes current state and is rewritten on an approved correction

`intent` SHALL describe the design as currently approved, never a round-by-round history.
When a mid-build clarification or correction changes what is being built, the orchestrator
SHALL rewrite `intent` to the new approved reading -- deleting the superseded wording
rather than appending to it -- in the same turn it appends the entry to `request_log`.
`request_log` remains append-only and is the sole record of the rounds. This is the same
current-state rule that already binds `planning_notes` and `part_notes`.

`BUILD_PLAN.json` SHALL carry an optional `intent_ts` field holding the ISO-8601 UTC
timestamp of the newest `request_log` entry that `intent` has been reconciled against. It
records acknowledgement, not edit: the orchestrator SHALL advance `intent_ts` to the
appended entry's `ts` in the same turn it appends any `clarification` or `correction`
entry, whether or not the entry caused `intent` to be rewritten. Phase 1 SHALL write
`intent_ts` alongside the approved reformulation at its exit checkpoint, set to the
`initial` entry's `ts`.

#### Scenario: Correction changes the design

- **WHEN** the user asks mid-build for a drain slot in the base
- **THEN** the `correction` entry is appended to `request_log` verbatim, `intent` is
  rewritten to describe a base that has a drain slot, and `intent_ts` is advanced to that
  entry's `ts`

#### Scenario: Superseded intent wording is deleted

- **WHEN** a correction replaces a fixed rake with an adjustable one
- **THEN** `intent` describes only the adjustable rake and carries no "previously fixed"
  or "ROUND 2" annotation

#### Scenario: Correction changes nothing about the design

- **WHEN** the user's correction only restates something `intent` already says
- **THEN** the entry is appended to `request_log`, `intent` is left unchanged, and
  `intent_ts` is still advanced to that entry's `ts`

#### Scenario: Phase 1 stamps the approved reformulation

- **WHEN** the Phase 1 exit checkpoint is approved and `intent` is written
- **THEN** `intent_ts` is written at the same time, set to the `initial` entry's `ts`

### Requirement: Sketches referenced by the approved intent are re-read before authoring

When `intent` references one or more `sketches/` paths, the orchestrator SHALL read those
files before authoring or re-authoring any part, not only when a `request_log` entry's
`images` field names them.

#### Scenario: Opening request carried a photo

- **WHEN** `intent` references `sketches/bracket-2026-09-01T10-00-00Z.jpg` and the first
  part is about to be authored
- **THEN** the orchestrator reads that image before writing the part script

### Requirement: Plan validation fails when `request_log` has moved past `intent_ts`

`plan_validate.validate_plan` SHALL report a blocking error when a plan's `request_log`
contains any `clarification` or `correction` entry whose `ts` is strictly newer than the
plan's `intent_ts`, or when such an entry exists and `intent_ts` is absent. The error
message SHALL name the unreconciled entries so the required rewrite is unambiguous.

Because the quality gate validates the plan through `plan_validate.validate_plan`, this
error SHALL surface as a `plan_invalid` gate issue with no separate gate check. The rule
SHALL be purely structural: it asserts that reconciliation was performed, and makes no
judgement about whether the rewritten `intent` is a correct reading -- that judgement
remains the advisory request-conformance bar's.

A `ts` or `intent_ts` value that cannot be parsed as an ISO-8601 timestamp SHALL itself be
reported as an error rather than compared.

#### Scenario: Correction appended without reconciling intent

- **WHEN** a plan carries a `correction` entry timestamped after its `intent_ts`
- **THEN** `validate_plan` returns an error naming that entry, the standalone validator
  exits non-zero, and the quality gate emits a `plan_invalid` issue that blocks a clean
  pass

#### Scenario: Correction appended and reconciled

- **WHEN** a plan's `intent_ts` equals the `ts` of its newest `clarification`/`correction`
  entry
- **THEN** `validate_plan` returns no staleness error

#### Scenario: Plan with no mid-build entries

- **WHEN** a plan's `request_log` holds only an `initial` entry, or no `request_log` at all
- **THEN** no staleness error is reported and `intent_ts` is not required

#### Scenario: Entries exist but the stamp is missing

- **WHEN** a plan carries a `clarification` entry and no `intent_ts` field
- **THEN** `validate_plan` returns an error, because an absent stamp with mid-build entries
  present means the reconciliation was never recorded

#### Scenario: Unparseable timestamp

- **WHEN** a plan's `intent_ts` is not a parseable ISO-8601 timestamp
- **THEN** `validate_plan` returns an error naming the bad value instead of comparing it

### Requirement: Appending an entry can record reconciliation in one command

`log.py request add` SHALL accept a `--reconciled` flag that sets the plan's
`intent_ts` to the `ts` of the entry it just appended. The flag SHALL be opt-in: an `add`
without it SHALL leave `intent_ts` unchanged, so the plan fails validation until the
intent is dealt with. The resulting plan SHALL be validated against
`build_plan_schema.json` before writing, as `add` already does.

#### Scenario: Append with reconciliation

- **WHEN** `log.py request add PLAN --kind correction --text "..." --reconciled` is
  run after `intent` has been rewritten
- **THEN** the entry is appended and `intent_ts` is set to that entry's `ts`, and the plan
  validates clean

#### Scenario: Append without reconciliation

- **WHEN** the same command is run without `--reconciled`
- **THEN** the entry is appended, `intent_ts` is left as it was, and a subsequent
  `plan.py validate` run fails naming the new entry
