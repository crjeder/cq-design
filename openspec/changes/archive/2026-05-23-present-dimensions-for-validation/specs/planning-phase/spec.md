## MODIFIED Requirements

### Requirement: Plan is shown to user for review before loop starts
The system SHALL display the generated `BUILD_PLAN.json` to the user and pause for confirmation or edits before the orchestration loop begins.

A dimension-validation checkpoint SHALL occur before `BUILD_PLAN.json` is generated (see `dimension-validation-checkpoint` spec). Confirmation of that checkpoint does not substitute for review of the final plan — both pauses are required.

#### Scenario: User approves plan
- **WHEN** user confirms the plan without changes
- **THEN** orchestrator proceeds to Phase 3 (build)

#### Scenario: User edits plan
- **WHEN** user modifies a dimension in the plan file
- **THEN** the skill re-validates the edited file and then proceeds

#### Scenario: Dimension checkpoint precedes plan generation
- **WHEN** the model involves any real-world product requiring dimension research
- **THEN** the dimension-validation table is presented and approved BEFORE `BUILD_PLAN.json` is generated, and the final plan review occurs AFTER generation
