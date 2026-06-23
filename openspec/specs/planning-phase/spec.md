# Planning Phase

## Purpose

Defines requirements for the planning phase: the prompt that produces `BUILD_PLAN.json` and the schema that file must conform to.

## Requirements

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

A dimension-validation checkpoint SHALL occur before `BUILD_PLAN.json` is generated (see `dimension-validation-checkpoint` spec). Confirmation of that checkpoint does not substitute for review of the final plan -- both pauses are required.

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

#### Scenario: Dimension checkpoint precedes plan generation
- **WHEN** the model involves any real-world product requiring dimension research
- **THEN** the dimension-validation table is presented and approved BEFORE `BUILD_PLAN.json` is generated, and the final plan review occurs AFTER generation

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

---

### Requirement: Part prompt instructs LLM not to write block imports
The `prompts/part.md` template SHALL explicitly instruct the LLM that block functions are pre-imported by the runner and that the LLM SHALL NOT write import statements for them.

The script structure section of `prompts/part.md` SHALL NOT contain a placeholder comment suggesting the LLM write `from blocks import ...` lines.

#### Scenario: Block functions called without imports in generated code
- **WHEN** the LLM generates a part script for a part with `blocks_needed: ["hollow_box"]`
- **THEN** the generated code calls `hollow_box(...)` directly without a preceding import statement for it

#### Scenario: Prompt template contains no import placeholder
- **WHEN** `prompts/part.md` is rendered for any part
- **THEN** the rendered prompt contains no comment or instruction suggesting the LLM write `from blocks import` lines

---

### Requirement: Build plan carries an optional per-part load hint
The build plan SHALL allow a part to optionally declare a `load` hint: the principal load
direction in the part's own authored frame, used to drive print-orientation strength
scoring. Plan validation SHALL accept the field when present (a direction in the authored
frame) and SHALL accept parts that omit it. When a part declares `load`, the planning
summary SHALL surface it; when absent, downstream strength scoring infers a load axis from
geometry.

#### Scenario: Plan with a declared load validates
- **WHEN** a build plan declares a `load` direction on a part
- **THEN** plan validation accepts it and the value is available to the orientation
  optimizer

#### Scenario: Plan without a load hint is still valid
- **WHEN** a part omits the `load` hint
- **THEN** plan validation accepts the part and strength scoring falls back to a
  geometry-inferred load axis

---

### Requirement: Build plan carries an optimization-mode preference

The build plan SHALL allow the user's print-optimization priority to be recorded as an
`optimize_for` preference, one of `strength`, `min_support`, or `visual_quality`, at the
plan level, with an optional per-part override of the same field. Plan validation SHALL
accept the field when present and SHALL accept plans and parts that omit it. The effective
mode for a part SHALL be its own `optimize_for` when present, otherwise the plan-level
value, otherwise `strength`. The planning phase SHALL record the mode from the user's stated
priority, and the effective mode SHALL be available to the print-orientation optimizer.

#### Scenario: Plan-level optimization mode validates

- **WHEN** a build plan declares `optimize_for: "visual_quality"` at the plan level
- **THEN** plan validation accepts it and the value is available to the orientation optimizer
  for every part lacking its own override

#### Scenario: Per-part override wins over the plan default

- **WHEN** a plan declares a plan-level `optimize_for` and one part declares a different
  `optimize_for`
- **THEN** that part's effective mode is its own value and the other parts use the plan-level
  value

#### Scenario: Plan without an optimization mode defaults to strength

- **WHEN** a plan omits `optimize_for` entirely
- **THEN** plan validation accepts it and every part's effective mode is `strength`

---

### Requirement: Build plan carries an optional per-part cosmetic surface

The build plan SHALL allow a part to optionally declare a `show_face` hint: the outward
normal of the part's primary cosmetic surface in its own authored frame, used by the
`visual_quality` optimization mode as the surface to orient face-down. Plan validation SHALL
accept the field when present and SHALL accept parts that omit it. When a part omits
`show_face`, the orientation optimizer infers a cosmetic surface from geometry.

#### Scenario: Plan with a declared cosmetic surface validates

- **WHEN** a part declares a `show_face` direction
- **THEN** plan validation accepts it and the value is available to the orientation optimizer

#### Scenario: Plan without a cosmetic surface is still valid

- **WHEN** a part omits the `show_face` hint
- **THEN** plan validation accepts the part and the optimizer infers a cosmetic surface when
  the visual-quality mode is active
