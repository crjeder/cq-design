## ADDED Requirements

### Requirement: A journal.py append command writes journal lines
The system SHALL provide `src/journal.py`, a stdlib-only script invoked as
`journal.py append <journal_path> <milestone> <text>`, where `<milestone>` is a
`<phase>/<milestone_key>` string (e.g. `phase3/part_accepted:lid`). The command SHALL
append exactly one line of the form `- <milestone>: <text>` to `<journal_path>`,
creating the file if it does not yet exist, and SHALL NOT rewrite, reorder, or remove
any existing line. The skill SHALL use this command wherever a phase document
currently describes appending a journal line by hand.

#### Scenario: Appending a milestone line
- **WHEN** `journal.py append build/journal.md phase3/part_accepted:lid "audit passed"`
  is run
- **THEN** the line `- phase3/part_accepted:lid: audit passed` is appended to
  `build/journal.md`, and any lines already in the file are unchanged

#### Scenario: File does not yet exist
- **WHEN** `journal.py append` is run against a path with no existing file
- **THEN** the file is created containing exactly the one appended line

#### Scenario: Repeated milestone key
- **WHEN** a later call appends a line whose milestone key was already used earlier in
  the file (a part rebuilt after a correction)
- **THEN** the new line is appended after the existing lines; the earlier line is left
  in place, not replaced
