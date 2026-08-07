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
| Status | One of: `confirmed` (two agreeing sources), `single-source`, `conflict` (sources disagree), `missing` |

The skill SHALL NOT generate `BUILD_PLAN.json` until the user has acknowledged or corrected the table.

#### Scenario: All dimensions confirmed from two sources
- **WHEN** every looked-up dimension was found in two agreeing sources
- **THEN** the table shows all rows with status `confirmed` and the skill asks the user to approve

#### Scenario: One dimension has only a single source
- **WHEN** a dimension was found in only one source
- **THEN** that row shows status `single-source` and the skill asks the user to confirm before proceeding

#### Scenario: Sources conflict
- **WHEN** two sources give different values for the same dimension
- **THEN** that row shows both values and status `conflict`, and the skill asks the user to provide the correct value

#### Scenario: Dimension not found
- **WHEN** a required dimension could not be found in any source
- **THEN** that row shows `-1` and status `missing`, and the skill asks the user for the correct value before continuing

---

### Requirement: User corrections are applied to the generated plan
If the user provides a corrected value for any dimension during the checkpoint review, the skill SHALL use the corrected value when generating `BUILD_PLAN.json`, not the looked-up value.

#### Scenario: User corrects a value inline
- **WHEN** the user says "the depth should be 8.5, not 8.0"
- **THEN** the plan uses 8.5 mm for that dimension

#### Scenario: User approves without changes
- **WHEN** the user confirms the table is correct
- **THEN** the plan uses all looked-up values as presented

