## Purpose

Repo-level hygiene invariants, enforced by `tests/test_process_hygiene.py`: every test file is reached by the test run, tests are never retried, and `src/` holds no unregistered one-off scripts.
## Requirements

### Requirement: Every test file is reached by the test run
The repository SHALL run every `tests/test_*.py` file in the default pytest run. Pytest configuration and `conftest.py` SHALL NOT exclude a test file (`--ignore`, `--deselect`, `collect_ignore`), and any CI configuration present SHALL invoke pytest on the whole `tests/` tree without a file path or `-k` filter.

#### Scenario: Exclusion option added
- **WHEN** `pyproject.toml` `addopts` or `conftest.py` excludes a test file
- **THEN** the hygiene test fails naming the exclusion

#### Scenario: CI runs a subset
- **WHEN** a CI config's pytest step names a single test file or passes `-k`
- **THEN** the hygiene test fails naming the config file and the step

#### Scenario: No CI config present
- **WHEN** the repository contains no CI config
- **THEN** the CI clause is skipped and the pytest-configuration clause is still checked

### Requirement: Flaky tests are fixed or deleted, never retried
The repository SHALL NOT retry tests. It SHALL NOT depend on a rerun or flaky plugin, SHALL NOT pass `--reruns`, SHALL NOT use `@pytest.mark.flaky`, and SHALL NOT wrap an assertion in a retry loop. Every `skip` and `skipif` SHALL state a reason and every `xfail` SHALL be `strict=True`.

#### Scenario: Retry plugin added
- **WHEN** `pyproject.toml` lists `pytest-rerunfailures`, `flaky` or `pytest-retry`
- **THEN** the hygiene test fails naming the dependency

#### Scenario: Skip without a reason
- **WHEN** a test uses `@pytest.mark.skip` or `skipif` with no `reason`
- **THEN** the hygiene test fails naming the file and line

#### Scenario: Non-strict xfail
- **WHEN** a test uses `xfail` without `strict=True`
- **THEN** the hygiene test fails naming the file and line

### Requirement: No one-off helper scripts in src
Every `src/*.py` module SHALL have a line in `FILES.md`, a contract entry in `reference/scripts.md`, and at least one file under `tests/` that references its module name. A module that lacks any of the three is a one-off helper and SHALL be deleted, moved out of `src/`, or documented and tested.

#### Scenario: Undocumented script
- **WHEN** `src/foo.py` exists with no `FILES.md` line
- **THEN** the hygiene test fails naming `src/foo.py` and the missing index

#### Scenario: Untested script
- **WHEN** no file under `tests/` mentions `foo`
- **THEN** the hygiene test fails naming `src/foo.py`

#### Scenario: Fully registered script
- **WHEN** a `src/*.py` has a `FILES.md` line, a `reference/scripts.md` entry and a referencing test
- **THEN** the hygiene test passes for it
