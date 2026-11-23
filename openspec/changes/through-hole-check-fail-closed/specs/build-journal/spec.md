## MODIFIED Requirements

### Requirement: A log.py journal append command writes journal lines

The system SHALL provide `src/log.py`, a stdlib-only script whose `journal append`
subcommand (`log.py journal append <journal_path> <key> <text>`) appends exactly one line
of the form `- <key>: <text>` to `<journal_path>`, where `<key>` is a `<phase>/<name>`
string (e.g. `phase0/restart`). The command SHALL create `<journal_path>` if it does not
yet exist, and SHALL NOT rewrite, reorder, or remove any existing line. It SHALL refuse,
with exit code 1 and without writing, any key whose base (the part before `:`) is a
`pipeline.py` milestone, and its error SHALL name `pipeline.py advance`: milestones are
written only by `pipeline.py advance`, which checks prerequisites and adds the `b1=` and
`sha=` records.

#### Scenario: Appending a restart marker
- **WHEN** `log.py journal append build/journal.md phase0/restart "again"` is run
- **THEN** the line `- phase0/restart: again` is appended to `build/journal.md`, and any
  lines already in the file are unchanged

#### Scenario: Pipeline milestone refused
- **WHEN** `log.py journal append build/journal.md phase2/plan_approved "ok"` is run
- **THEN** it exits 1, the journal is unchanged, and stderr names `pipeline.py advance`

#### Scenario: File does not yet exist
- **WHEN** `log.py journal append` is run with a non-milestone key against a path with no
  existing file
- **THEN** the file is created containing exactly the one appended line

#### Scenario: Repeated key
- **WHEN** a later call appends a line whose key was already used earlier in the file
- **THEN** the new line is appended after the existing lines; the earlier line is left
  in place, not replaced
