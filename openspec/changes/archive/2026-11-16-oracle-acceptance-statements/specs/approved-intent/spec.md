## ADDED Requirements

### Requirement: The approved intent and the oracle statements are approved together

The Phase 1 exit checkpoint SHALL present the oracle's statements (per the
`oracle-acceptance` spec) alongside the reformulation, and a single approval SHALL cover
both. A statement the user corrects SHALL be treated as a correction of the reformulation:
the corrected reading is written into the reformulation, which becomes `intent` on
approval, and the oracle is re-run against it. The approved `intent` SHALL therefore
contain the text that every approved statement cites.

#### Scenario: Statement correction changes the intent

- **WHEN** the user rejects a statement "hook opening accepts a 24 mm handle" and says the
  handle is 28 mm
- **THEN** the reformulation is amended to 28 mm, the oracle is re-run, and the approved
  `intent` contains the text the revised statement cites

#### Scenario: Approval without statements

- **WHEN** the checkpoint is prepared and `acceptance.json` is missing or invalid
- **THEN** approval is not accepted until the oracle has produced a valid file
