## ADDED Requirements

### Requirement: Input file failures are reported as file_error
When a script that emits a JSON contract cannot read a required input file (missing, directory, unreadable, or invalid JSON), it SHALL report an entry with `type: "file_error"`, a `message` naming the file and cause, and a `hint` naming the flag or pipeline step that produces it (in `errors` for `run_cadquery_model.py`, in `issues` for `quality_gate.py`), and SHALL exit 1 with the contract keys still present.

#### Scenario: Missing plan passed to quality gate
- **WHEN** `quality_gate.py` is given a `--plan` path that does not exist
- **THEN** stdout JSON has `passed: false` and `issues` contains one `file_error` entry naming the path, with no traceback in `stderr`

#### Scenario: Missing print-rotate file passed to the wrapper
- **WHEN** `run_cadquery_model.py` is given a `--print-rotate` path that does not exist
- **THEN** stdout JSON has `success: false`, every contract key is present, and `errors` contains one `file_error` entry

#### Scenario: Clean run
- **WHEN** all input files are readable
- **THEN** no `file_error` entry appears in `errors`
