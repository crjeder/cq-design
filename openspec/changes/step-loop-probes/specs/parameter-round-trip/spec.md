## ADDED Requirements

### Requirement: Step scripts have nothing to import
`plan.py import-params` SHALL report `not_applicable` with no pending writes and exit 0
when the script is a step script (it uses `Part` and has no `PARAMETERS` block), since
its dimensions are read from the plan.

#### Scenario: Import from a step script
- **WHEN** `plan.py import-params build/plate.py --part plate --write` runs on a step
  script
- **THEN** the report has `status: "not_applicable"`, the plan is not modified, and the
  exit code is 0
