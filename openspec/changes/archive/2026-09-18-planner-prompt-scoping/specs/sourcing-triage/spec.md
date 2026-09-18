## MODIFIED Requirements

### Requirement: License check is mandatory at reuse rungs
At rungs 1-4 the source model's license SHALL be identified before reuse. The Sourcing
agent (see `sourcing-prompt-rendering`) SHALL derive and return a per-candidate
reusability verdict in its return table: a missing or unstated license SHALL be reported
as not reusable (all-rights-reserved); an ND (no-derivatives) license SHALL be reported
as blocking rungs 1, 2, and 4, with a rung-3-only verdict when the license permits
unmodified redistribution and a fully-blocked verdict when it does not. The main session
SHALL trust the agent's verdict rather than re-deriving reusability from the raw license
string, and SHALL treat a rung as not fitting for any candidate whose verdict blocks it.
The license name, source URL, chosen rung, and verdict SHALL be recorded - in
`planning_notes` when a BUILD_PLAN exists, otherwise in the delivery summary - and shown
to the user at the reuse decision.

#### Scenario: ND-licensed parametric source
- **WHEN** rung 1 matches a CC BY-ND licensed OpenSCAD source and the agent's verdict for
  that candidate blocks rungs 1, 2, and 4
- **THEN** rung 1 is rejected for that candidate and classification continues without the
  main session re-deriving the ND rule itself

#### Scenario: No license stated
- **WHEN** a found model page states no license and the agent returns a not-reusable
  verdict for it
- **THEN** the candidate is treated as all-rights-reserved and not reused

#### Scenario: Rung-3 ND exception
- **WHEN** an ND-licensed mesh's verdict is rung-3-only because its license permits
  unmodified redistribution
- **THEN** the mesh MAY be delivered unmodified at rung 3 but does not fit rungs 1, 2, or 4

#### Scenario: Provenance recorded
- **WHEN** any rung 1-4 reuse is accepted
- **THEN** the license, source URL, rung, and the agent's verdict are recorded in
  `planning_notes` (or the delivery summary when no plan exists) and stated to the user
