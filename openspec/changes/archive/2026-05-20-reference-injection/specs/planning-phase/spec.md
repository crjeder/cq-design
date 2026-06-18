## MODIFIED Requirements

### Requirement: Planning prompt produces structured BUILD_PLAN
The system SHALL provide a `prompts/planning.md` prompt that, when invoked with a user's model description and rendered with `{{USER_REQUEST}}`, `{{BLOCK_INVENTORY}}`, and `{{FDM_GUIDELINES}}`, produces a valid `BUILD_PLAN.json` file conforming to the defined schema.

The `{{FDM_GUIDELINES}}` placeholder SHALL be substituted with sections from `reference/FDM 3D Print Design Guidelines.md` matching the union of all `blocks_needed` across all parts in the plan, plus sections tagged `always`. This substitution is performed by the skill before invoking the LLM, not by `orchestrate.py`.

#### Scenario: Single-part model
- **WHEN** user describes a simple enclosure for an Arduino Nano
- **THEN** planning prompt produces a `BUILD_PLAN.json` with one part entry, printer/material constraints, and at least one interface entry for the USB port

#### Scenario: Multi-part model
- **WHEN** user describes a hinged box with a snap-fit lid
- **THEN** planning prompt produces a `BUILD_PLAN.json` with at least two part entries and an assembly strategy entry

#### Scenario: Dimension research required
- **WHEN** the model involves a known real-world product (phone, PCB, connector)
- **THEN** the planning prompt instructs the LLM to perform web search for exact dimensions before populating the plan

#### Scenario: FDM guidelines present in planning prompt
- **WHEN** the planning prompt is rendered for any model
- **THEN** the rendered prompt contains relevant FDM guideline sections at the `{{FDM_GUIDELINES}}` location
