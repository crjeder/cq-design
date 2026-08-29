## ADDED Requirements

### Requirement: REQUIREMENTS.md written at Phase 1 approval

Phase 1 SHALL write `REQUIREMENTS.md` at the project root, in the same turn as the
`parameters.py` provenance write, whenever the request involved topology ambiguity, a
real-world dimension lookup, or a stated fit type. The file SHALL contain, at minimum:
intent, the confirmed topology reading (or its absence), the dimension table, fit
requirements per mating interface, the resolved DFM constraints noting whether each
came from `printer_profile.json`'s default or a stated one-time exception, and any
open questions or assumptions left unresolved.

#### Scenario: Request has topology ambiguity

- **WHEN** Phase 1 illustrates a shape reading and the user confirms or corrects it
- **THEN** `REQUIREMENTS.md` is written with the confirmed reading recorded under
  "Topology"

#### Scenario: Request needs a real-world dimension lookup

- **WHEN** the Dimension validation checkpoint table is approved by the user
- **THEN** `REQUIREMENTS.md` is written with that table recorded under "Dimensions"

#### Scenario: Request states a fit type for a mating surface

- **WHEN** the user specifies press/snap/sliding/loose fit for any interface
- **THEN** `REQUIREMENTS.md` is written with that fit type recorded under "Fit
  requirements"

#### Scenario: Request resolves nothing beyond bare user-stated numbers

- **WHEN** the request has no topology ambiguity, no real-world dimension lookup, and
  no stated fit type
- **THEN** `REQUIREMENTS.md` is not written, and no `phase1/requirements_written`
  journal line is appended

### Requirement: Every section present regardless of content

Each of the five sections (Intent, Topology, Dimensions, Fit requirements, Printer &
DFM constraints, Open questions/assumptions) SHALL appear in the file even when there
is nothing to report for it, using an explicit placeholder sentence rather than
omitting the section.

#### Scenario: A section has nothing to report

- **WHEN** the request has no mating surfaces
- **THEN** the "Fit requirements" section is present with the text "No mating surfaces
  in this request." rather than being omitted

### Requirement: Amended in place by Phase 2, never regenerated

If Phase 2 planning introduces or changes a requirement not already captured in
`REQUIREMENTS.md`, Phase 2 SHALL amend the relevant section of the existing file in
place. It SHALL NOT regenerate the file from scratch, and SHALL NOT amend it when
Phase 1 skipped the file entirely or when planning added nothing new.

#### Scenario: Planning introduces a new fit constraint

- **WHEN** Phase 2 planning determines a snap-fit tolerance not discussed in Phase 1
- **THEN** the "Fit requirements" section of the existing `REQUIREMENTS.md` is amended
  to record it, and the rest of the file is left untouched

#### Scenario: Phase 1 skipped the file

- **WHEN** `REQUIREMENTS.md` was never written because Phase 1's skip condition applied
- **THEN** Phase 2 does not create it

### Requirement: Journal milestone on write

Phase 1 SHALL append a `- phase1/requirements_written: REQUIREMENTS.md written` line to
`build/journal.md` in the same turn the file is written, and SHALL skip this line
whenever the file itself is skipped.

#### Scenario: File written

- **WHEN** `REQUIREMENTS.md` is written per the triggers above
- **THEN** `build/journal.md` gains a `phase1/requirements_written` line

#### Scenario: File skipped

- **WHEN** `REQUIREMENTS.md` is skipped
- **THEN** no `phase1/requirements_written` line is appended
