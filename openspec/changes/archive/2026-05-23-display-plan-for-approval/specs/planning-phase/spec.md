## MODIFIED Requirements

### Requirement: Plan is shown to user for review before loop starts
The system SHALL write `BUILD_PLAN.json` to disk after validation passes, then display a human-readable Markdown summary of the plan to the user and pause for confirmation or edits before the orchestration loop begins. The path written to disk SHALL be shown alongside the summary. The raw JSON SHALL NOT be displayed in the chat; only the summary is shown.

The summary SHALL include the following sections:
- Printer, material, and nozzle diameter
- Parts table: ID, description, W x D x H dimensions, print orientation, and blocks_needed
- Interfaces table: one row per interface entry across all parts, showing part ID, type, connector (if any), wall, and position
- Assembly strategy: one-line description (omitted for single-part models)
- Constraints: wall_min_mm, overhang_max_deg, dimension_tolerance_mm

#### Scenario: User approves plan
- **WHEN** user confirms the plan without changes
- **THEN** orchestrator proceeds to Phase 3 using the file already written to disk

#### Scenario: User edits plan
- **WHEN** user modifies a dimension in the plan file on disk
- **THEN** orchestrator re-validates the edited file from disk and then proceeds

#### Scenario: Plan written before display
- **WHEN** the planning phase produces a valid plan
- **THEN** `BUILD_PLAN.json` exists on disk before the user is shown the summary

#### Scenario: Summary shows all parts
- **WHEN** the plan contains three parts
- **THEN** the summary table contains exactly three rows, one per part, with correct IDs and dimensions

#### Scenario: No raw JSON in chat
- **WHEN** the plan is displayed for approval
- **THEN** the chat message contains no fenced JSON code block -- only the Markdown summary and the file path

#### Scenario: Multi-part plan shows assembly strategy
- **WHEN** the plan has more than one part
- **THEN** the summary includes an assembly strategy line from the plan's `assembly` field

#### Scenario: Single-part plan omits assembly strategy
- **WHEN** the plan has exactly one part
- **THEN** the summary contains no assembly strategy section
