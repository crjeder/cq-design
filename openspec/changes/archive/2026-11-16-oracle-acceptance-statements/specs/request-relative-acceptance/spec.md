## ADDED Requirements

### Requirement: Visual oracle statements are blocking checklist questions

When `acceptance.json` exists, every `visual` statement bound to the part under review (or
bound to `"*"`) SHALL be added to that review's Visual Review Checklist as a question
labelled with its statement id and `text`. Both the progressive self-review and the
implementation audit SHALL answer it. A "no" SHALL be recorded as a blocking
`visual_mismatch` naming the statement id and the cited view, and SHALL take part in the
existing retry budget. A statement still answered "no" after 3 rounds SHALL be escalated
to the user with the same choices as an `oracle_unmet` escalation. This requirement does
not change the advisory severity of the free-form request-conformance finding.

#### Scenario: Visual statement fails review

- **WHEN** `S7` "rounded, friendly look" is bound to the part and the auditor answers it
  "no" citing the iso view
- **THEN** a blocking `visual_mismatch` naming `S7` and the iso view is recorded and the
  builder is resumed with it

#### Scenario: Free-form finding stays advisory

- **WHEN** the reviewer also notes a request-conformance discrepancy not covered by any
  statement or checklist question
- **THEN** it is recorded as advisory, as before

#### Scenario: Auditor input still excludes the script

- **WHEN** the audit prompt is rendered with visual statements added
- **THEN** it contains the statement texts and no part script source
