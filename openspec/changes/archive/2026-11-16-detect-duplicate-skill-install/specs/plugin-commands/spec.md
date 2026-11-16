## MODIFIED Requirements

### Requirement: init prepares a working directory

`/cq-design:init` SHALL run `uv sync`, `init_permissions.py`, and profile validation, idempotently, and report any seeded file and validation errors. It SHALL also run `install_check.py` and, when `duplicate` is true, warn the user without removing either copy or failing.

#### Scenario: Re-run
- **WHEN** `/cq-design:init` runs twice
- **THEN** the second run changes nothing and overwrites no seeded file

#### Scenario: Duplicate install
- **WHEN** `install_check.py` reports `duplicate` true
- **THEN** init shows the warning and the removal hint and still completes the rest of setup

### Requirement: status is read-only

`/cq-design:status` SHALL report the installed skill version (`skill_version.py`), bundle staleness (`bundle_project.py --check`), profile validity, and duplicate-install state (`install_check.py`), and SHALL NOT modify any file.

#### Scenario: Stale bundle
- **WHEN** the project's bundle stamp differs from the installed commit
- **THEN** status reports it and suggests `/cq-design:update`

#### Scenario: Duplicate install
- **WHEN** `install_check.py` reports `duplicate` true
- **THEN** status reports both locations and, if `commits_differ`, says the copies are at different commits
