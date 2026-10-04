## ADDED Requirements

### Requirement: build.py reports progress

`build.py` SHALL print progress to stdout, flushed per line, while building. Each unit of work SHALL be reported as `[k/N] <step> <id>`, where `N` is the number of units in that phase and `k` counts from 1. Phases SHALL be counted separately; no cross-phase percentage SHALL be reported. Unions whose accepted orientation is reused unchanged SHALL NOT be reported in the orientation phase. The existing final summary and the `build failed:` message on stderr SHALL be unchanged.

#### Scenario: Parts loaded

- **WHEN** `build.py` runs on a plan with three parts
- **THEN** it prints `[1/3]`, `[2/3]` and `[3/3]` loading lines, each naming a part id, before the final summary

#### Scenario: Orientation reused

- **WHEN** every union has a fresh accepted orientation in `orientations.json`
- **THEN** no orientation progress lines are printed

#### Scenario: Orientation recomputed

- **WHEN** two unions have no accepted orientation or a stale one
- **THEN** exactly two orientation lines `[1/2]` and `[2/2]` are printed, naming those unions

#### Scenario: Progress is live when piped

- **WHEN** `build.py` stdout is a pipe
- **THEN** each progress line is flushed as it is printed rather than at process exit

#### Scenario: Failure

- **WHEN** a part script fails to load
- **THEN** `build failed: ...` is written to stderr and the exit code is non-zero, as before
