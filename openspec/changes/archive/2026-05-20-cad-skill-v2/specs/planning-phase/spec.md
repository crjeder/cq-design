> **Superseded by** `openspec/changes/improve-planning-prompt/specs/planning-phase/spec.md`
> Requirements for `print_orientation`, clearance, planning_notes/part_notes, and single-part assembly rules have been updated there.

## ADDED Requirements

### Requirement: Planning prompt produces structured BUILD_PLAN
The system SHALL provide a `prompts/planning.md` prompt that, when invoked with a user's model description, produces a valid `BUILD_PLAN.json` file conforming to the defined schema.

#### Scenario: Single-part model
- **WHEN** user describes a simple enclosure for an Arduino Nano
- **THEN** planning prompt produces a `BUILD_PLAN.json` with one part entry, printer/material constraints, and at least one interface entry for the USB port

#### Scenario: Multi-part model
- **WHEN** user describes a hinged box with a snap-fit lid
- **THEN** planning prompt produces a `BUILD_PLAN.json` with at least two part entries and an assembly strategy entry

#### Scenario: Dimension research required
- **WHEN** the model involves a known real-world product (phone, PCB, connector)
- **THEN** the planning prompt instructs the LLM to perform web search for exact dimensions before populating the plan

---

### Requirement: BUILD_PLAN.json schema is validated before the loop starts
The system SHALL validate `BUILD_PLAN.json` against its schema before the orchestration loop begins, failing fast with a descriptive error if required fields are missing or malformed.

#### Scenario: Valid plan
- **WHEN** `BUILD_PLAN.json` contains all required fields
- **THEN** validation passes and the orchestrator proceeds

#### Scenario: Missing required field
- **WHEN** a part entry is missing its `dimensions` field
- **THEN** validation fails with an error naming the part and missing field before any code is generated

---

### Requirement: BUILD_PLAN.json schema includes part decomposition, interfaces, and block selection
The `BUILD_PLAN.json` schema SHALL include the following top-level fields:

- `schema_version` (integer, required)
- `intent` (string, required)
- `printer` (string, required)
- `material` (string, required)
- `nozzle_mm` (number, required)
- `parts` (array of part objects, required, min 1)
- `assembly` (object, required if `parts` length > 1)
- `constraints` (object, required)

Each part object SHALL include:
- `id` (string, required, unique)
- `description` (string, required)
- `dimensions` (object with `w_mm`, `d_mm`, `h_mm`, required)
- `interfaces` (array, may be empty)
- `blocks_needed` (array of block names from inventory, may be empty)
- `print_orientation` (string, required)

#### Scenario: Part with physical interface
- **WHEN** a part has a USB-C port cutout
- **THEN** its `interfaces` array contains an entry with `type: "port_cutout"`, `connector: "usb_c"`, `wall`, and `position_mm`

#### Scenario: Part with no interfaces
- **WHEN** a part is a simple bracket with no connectors or mating surfaces
- **THEN** its `interfaces` array is empty and validation still passes

---

### Requirement: Plan is shown to user for review before loop starts
The system SHALL display the generated `BUILD_PLAN.json` to the user and pause for confirmation or edits before the orchestration loop begins.

#### Scenario: User approves plan
- **WHEN** user confirms the plan without changes
- **THEN** orchestrator proceeds to Phase 1

#### Scenario: User edits plan
- **WHEN** user modifies a dimension in the plan file
- **THEN** orchestrator re-validates the edited file and then proceeds
