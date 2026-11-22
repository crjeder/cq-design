# cadgenbench-work-retention Specification

## Purpose
TBD - created by archiving change drawing-profile-check. Update Purpose after archive.
## Requirements
### Requirement: Runner keeps fixture work directories

`evals/cadgenbench_run.py` SHALL keep `<run>/_work/<id>/` after generating each fixture and
SHALL delete only its `.venv/` directory, whether the fixture succeeded, failed, or timed
out. A failure to delete the venv SHALL NOT stop the run.

#### Scenario: Fixture finished
- **WHEN** a fixture's `claude -p` run returns
- **THEN** `<run>/_work/<id>/` still holds its part scripts, `BUILD_PLAN.json`, `build/`
  logs and `cost.json`, and has no `.venv/`

#### Scenario: Fixture timed out
- **WHEN** a fixture's run times out
- **THEN** its work directory is kept and its `.venv/` is removed

