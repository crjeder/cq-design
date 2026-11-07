# Dimension Validation Checkpoint

## Purpose

TBD - Defines requirements for the dimension-validation checkpoint that occurs before BUILD_PLAN.json is generated, ensuring looked-up dimensions are verified by the user before planning proceeds.
## Requirements
### Requirement: Found dimensions are presented in a structured table before plan generation
After all dimension research is complete and before generating `BUILD_PLAN.json`, the skill SHALL present a markdown table summarising every looked-up dimension with the following columns:

| Column | Content |
|--------|---------|
| Item | What was measured (e.g. "iPhone 15 Pro width") |
| Value (mm) | The found value, or `-1` if not found |
| Source | URL(s) consulted |
| Status | One of: `confirmed` (two agreeing sources), `single-source`, `conflict` (sources disagree), `assumed` (no source; a concrete starting value the skill picked), `missing` |

The table SHALL be presented together with the approved-intent reformulation
(`approved-intent` spec) as the single Phase 1 exit checkpoint, taking one approval from
the user for both. The skill SHALL NOT present the reformulation and the table as two
separate approval rounds.

The skill SHALL NOT generate `BUILD_PLAN.json` until the user has acknowledged or corrected the checkpoint, and SHALL NOT accept approval while any row remains `missing` or carries `-1`: such a row SHALL first be resolved to a sourced value, or converted to `assumed` with a concrete value the user accepts.

#### Scenario: All dimensions confirmed from two sources
- **WHEN** every looked-up dimension was found in two agreeing sources
- **THEN** the table shows all rows with status `confirmed` and the skill asks the user to approve it together with the reformulation

#### Scenario: One dimension has only a single source
- **WHEN** a dimension was found in only one source
- **THEN** that row shows status `single-source` and the skill asks the user to confirm before proceeding

#### Scenario: Sources conflict
- **WHEN** two sources give different values for the same dimension
- **THEN** that row shows both values and status `conflict`, and the skill asks the user to provide the correct value

#### Scenario: Dimension not found
- **WHEN** a required dimension could not be found in any source
- **THEN** that row shows `-1` and status `missing`, and the skill asks the user for the correct value before continuing

#### Scenario: A parameter-level unknown is assumed rather than asked
- **WHEN** a dimension has no source and guessing it wrong would cost only a parameter edit
- **THEN** the skill fills the row with a concrete value at status `assumed`, and the reformulation presented alongside names it as an assumption

#### Scenario: Approval is refused while a row is missing
- **WHEN** the user approves the checkpoint while one row still shows `-1` / `missing`
- **THEN** the skill does not proceed to Phase 2 and asks for that value or for permission to assume one

#### Scenario: Reformulation and table are approved in one round
- **WHEN** the Phase 1 exit checkpoint is presented
- **THEN** the reformulated request and the dimension table appear in the same message and one user approval covers both

---

### Requirement: User corrections are applied to the generated plan
If the user provides a corrected value for any dimension during the checkpoint review, the skill SHALL use the corrected value when generating `BUILD_PLAN.json`, not the looked-up value. If the user corrects the reformulation, the corrected reading SHALL be the text written to `intent`.

The skill SHALL write `parameters.py` in the caller's working directory as soon as the
user approves or corrects the checkpoint -- before Phase 2 starts -- recording every
dimension in the table with its corrected value, source, and status as a comment. This
is the durable record of the checkpoint's research; deferring it to Phase 2 loses it if
the session is interrupted between the two. Phase 2 updates the same file only when
planning introduces or changes a measurement.

#### Scenario: User corrects a value inline
- **WHEN** the user says "the depth should be 8.5, not 8.0"
- **THEN** the plan uses 8.5 mm for that dimension

#### Scenario: User corrects the reformulation inline
- **WHEN** the user says "the lid snaps on, it doesn't screw on"
- **THEN** the corrected reading is what is written to `intent`, and the correction is appended to `request_log`

#### Scenario: User approves without changes
- **WHEN** the user confirms the table is correct
- **THEN** the plan uses all looked-up values as presented

#### Scenario: An assumed value is recorded with its status
- **WHEN** the approved table carries a row at status `assumed`
- **THEN** `parameters.py` records that value with `assumed` noted in its comment, exactly as it does for `single-source` and `conflict`

#### Scenario: Provenance written at approval

- **WHEN** the user approves the dimension table
- **THEN** `parameters.py` is written in the same turn, and a journal milestone is
  appended, before the planning prompt is rendered

#### Scenario: Session interrupted after approval

- **WHEN** the session is cut off after the table is approved but before
  `BUILD_PLAN.json` exists
- **THEN** `parameters.py` holds every approved dimension and its source, so the
  resumed session re-runs no web lookups

### Requirement: The exit checkpoint includes the concept sketch

The Phase 1 exit checkpoint SHALL present the concept sketch (see `concept-sketch`) together with the dimension table. Approval SHALL cover both, and the `dimensions_approved` milestone SHALL be recorded only after both are approved.

#### Scenario: Both approved
- **WHEN** the user approves the dimensions and the sketch
- **THEN** `parameters.py` is written and `dimensions_approved` is journaled

#### Scenario: Sketch rejected
- **WHEN** the user rejects the sketch
- **THEN** no `dimensions_approved` milestone is written until a revised sketch is approved
