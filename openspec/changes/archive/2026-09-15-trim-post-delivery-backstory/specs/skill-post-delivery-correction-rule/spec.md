## ADDED Requirements

### Requirement: Post-delivery geometry corrections re-run downstream deterministic steps
A geometry-changing correction (a dimension, a feature, a hand-edit to a part script)
arriving after Phase 4 has already reported delivery SHALL be treated as re-opening
every deterministic step downstream of the affected union that Phase 4 already reported
as done: print-orientation optimization, model export, and the quality gate, each
re-run for the affected union(s) before Phase 4's delivery report is repeated. Unions
unaffected by the correction SHALL keep their previously accepted
`build/orientations.json` entry.

#### Scenario: Hand-edited part script after delivery
- **WHEN** a user asks for a geometry change to a part script after Phase 4 has already
  reported delivery for that union
- **THEN** the session re-runs print-orientation optimization, model export, and the
  quality gate for that union before re-reporting delivery, and does not report delivery
  against a stale `model.3mf`, STL, or `print_recipe`

#### Scenario: Correction to one union leaves others untouched
- **WHEN** a post-delivery correction changes geometry in only one of several unions
- **THEN** the unaffected unions keep their existing `build/orientations.json` entries
  and are not re-optimized
