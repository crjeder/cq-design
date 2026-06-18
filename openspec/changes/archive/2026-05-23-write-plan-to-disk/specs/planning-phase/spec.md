# Planning Phase (delta)

## MODIFIED Requirements

### Requirement: Plan is shown to user for review before loop starts

The system SHALL write `BUILD_PLAN.json` to disk after validation passes, then display the generated `BUILD_PLAN.json` to the user and pause for confirmation or edits before the orchestration loop begins. The path written SHALL be shown alongside the JSON display.

#### Scenario: User approves plan

- **WHEN** user confirms the plan without changes
- **THEN** orchestrator proceeds to Phase 3 using the file already written to disk

#### Scenario: User edits plan

- **WHEN** user modifies a dimension in the plan file on disk
- **THEN** orchestrator re-validates the edited file from disk and then proceeds

#### Scenario: Plan written before display

- **WHEN** the planning phase produces a valid plan
- **THEN** `BUILD_PLAN.json` exists on disk before the user is shown the JSON code block
