## ADDED Requirements

### Requirement: planning_notes and part_notes describe current state only
`prompts/planning.md` and `prompts/part.md` SHALL instruct that `planning_notes`
(plan-level design reasoning) and each part's `part_notes` describe the CURRENT design
state only -- decomposition choices, dimension sources, blocks chosen, geometry
rationale as of the present plan/script -- and SHALL NOT contain round-by-round build
history, dated "ROUND N" narrative, or "SUPERSEDED by round N" annotations.
Round-by-round history belongs exclusively in `request_log` (see the `request-log`
capability).

#### Scenario: Part notes stay current-state-only across correction rounds
- **WHEN** a part's design changes across several correction rounds
- **THEN** its `part_notes` after each round describes only the design as it now
  stands, with no retained narrative from prior rounds

#### Scenario: Planning notes do not narrate the plan's revision history
- **WHEN** a plan is regenerated after a correction (a re-plan)
- **THEN** the regenerated `planning_notes` describes the current decomposition/
  reasoning, not a log of what changed from the previous plan version (that history is
  in `request_log`)
