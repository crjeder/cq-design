## ADDED Requirements

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

#### Scenario: Correction changes the design

- **WHEN** the user asks mid-build for a drain slot in the base
- **THEN** the `correction` entry is appended to `request_log` verbatim, and `intent` is
  rewritten to describe a base that has a drain slot

#### Scenario: Superseded intent wording is deleted

- **WHEN** a correction replaces a fixed rake with an adjustable one
- **THEN** `intent` describes only the adjustable rake and carries no "previously fixed"
  or "ROUND 2" annotation

#### Scenario: Correction changes nothing about the design

- **WHEN** the user's correction only restates something `intent` already says
- **THEN** the entry is appended to `request_log` and `intent` is left unchanged

### Requirement: Sketches referenced by the approved intent are re-read before authoring

When `intent` references one or more `sketches/` paths, the orchestrator SHALL read those
files before authoring or re-authoring any part, not only when a `request_log` entry's
`images` field names them.

#### Scenario: Opening request carried a photo

- **WHEN** `intent` references `sketches/bracket-2026-09-01T10-00-00Z.jpg` and the first
  part is about to be authored
- **THEN** the orchestrator reads that image before writing the part script
