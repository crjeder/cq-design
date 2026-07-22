# Planning Phase

## Purpose

Defines requirements for the planning phase: the prompt that produces `BUILD_PLAN.json` and the schema that file must conform to.

## Requirements

### Requirement: Planning prompt produces structured BUILD_PLAN
The system SHALL provide a `prompts/planning.md` prompt that, when invoked with a user's model description and rendered with `{{USER_REQUEST}}`, `{{BLOCK_INVENTORY}}`, `{{FDM_GUIDELINES}}`, and `{{PRINTER_PROFILE}}`, produces a valid `BUILD_PLAN.json` file conforming to the defined schema.

The `{{FDM_GUIDELINES}}` placeholder SHALL be substituted with sections from `reference/FDM 3D Print Design Guidelines.md` matching the union of all `blocks_needed` across all parts in the plan, plus sections tagged `always`. This substitution is performed by the skill before invoking the LLM, not by `orchestrate.py`.

The `{{PRINTER_PROFILE}}` placeholder SHALL be substituted with the resolved `printer`, `material`, `nozzle_mm`, and `constraints` values from a validated `printer_profile.json` in the working directory, when one exists (see `printer-profile-config` spec). When `printer_profile.json` is absent or fails validation, the corresponding field(s) SHALL instead be asked of the user, exactly as when no profile exists. This substitution is performed by the skill before invoking the LLM, not by `orchestrate.py`.

When the user explicitly states a value for `printer`, `material`, `nozzle_mm`, or a `constraints` field that differs from the loaded profile, the resulting `BUILD_PLAN.json` SHALL use the user-stated value, AND the skill SHALL write that value back into `printer_profile.json` in the working directory as the new project-level default, announcing the change to the user in the same turn. If the user explicitly indicates the value is a one-time exception rather than a new default, the skill SHALL use the value for the current plan only and SHALL NOT write it back.

For multi-part models the planning prompt SHALL express assembly declaratively: each part is positioned with its `placement` and the whole model is treated as one assembly (the kinematic fixed set is every other union). The planning prompt SHALL NOT emit an `assembly` strategy object. Connection method (snap, screw, press, etc.) SHALL be expressed through the part `interfaces` and `blocks_needed` (e.g. `snap_hook_clip`, `screw_boss`) and narrated in `planning_notes`.

#### Scenario: Single-part model
- **WHEN** user describes a simple enclosure for an Arduino Nano
- **THEN** planning prompt produces a `BUILD_PLAN.json` with one part entry, printer/material constraints, and at least one interface entry for the USB port

#### Scenario: Multi-part model
- **WHEN** user describes a hinged box with a snap-fit lid
- **THEN** planning prompt produces a `BUILD_PLAN.json` with at least two part entries, each positioned by its `placement`, and snap-fit connection expressed through interfaces/blocks rather than an `assembly` strategy object

#### Scenario: Dimension research required
- **WHEN** the model involves a known real-world product (phone, PCB, connector)
- **THEN** the planning prompt instructs the LLM to perform web search for exact dimensions before populating the plan

#### Scenario: FDM guidelines present in planning prompt
- **WHEN** the planning prompt is rendered for any model
- **THEN** the rendered prompt contains relevant FDM guideline sections at the `{{FDM_GUIDELINES}}` location

#### Scenario: Printer profile present
- **WHEN** a valid `printer_profile.json` exists in the working directory and the user does not state a different printer/material/nozzle for this model
- **THEN** the rendered prompt's `{{PRINTER_PROFILE}}` location contains the profile's `printer`, `material`, `nozzle_mm`, and `constraints` values
- **AND** Phase 1 does not ask the user for those fields
- **AND** the resulting `BUILD_PLAN.json` uses those values

#### Scenario: Printer profile absent
- **WHEN** no `printer_profile.json` exists in the working directory, or it fails validation
- **THEN** Phase 1 asks the user for printer, material, nozzle, and constraints as it does today

#### Scenario: Per-model override wins over the profile and updates the project default
- **WHEN** a valid `printer_profile.json` exists but the user states a different nozzle diameter for the current model, without indicating it's a one-time exception
- **THEN** the resulting `BUILD_PLAN.json` uses the user-stated nozzle diameter
- **AND** `printer_profile.json` on disk is updated so `nozzle_mm` reflects the new value
- **AND** the skill tells the user the project default was updated

#### Scenario: Explicit one-time exception does not update the project default
- **WHEN** a valid `printer_profile.json` exists and the user states a different value for the current model but explicitly says it's a one-off, not a new default
- **THEN** the resulting `BUILD_PLAN.json` uses the user-stated value
- **AND** `printer_profile.json` on disk is left unchanged

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
- `constraints` (object, required)

The schema SHALL NOT define an `assembly` object, and SHALL NOT make any field
conditionally required on the number of parts. Multi-part assembly is expressed through
each part's `placement`.

Each part object SHALL include:
- `id` (string, required, unique)
- `description` (string, required)
- `dimensions` (object with `w_mm`, `d_mm`, `h_mm`, required)
- `interfaces` (array, may be empty)
- `blocks_needed` (array of block names from inventory, may be empty)
- `print_orientation` (string, required)

Each `interfaces[]` entry SHALL require `type` (string) and MAY carry structured,
machine-readable placement fields (all optional): `wall` (one of the six face names),
`position_mm` (`[x, y, z]`, the feature's intended center in the part's authored frame),
and a size field (`diameter_mm` for round features, or `size_mm` as `[w, h]` for
rectangular). These fields SHALL be defined in the schema (not free-form
`additionalProperties`), so a declared placement is machine-readable; they remain optional
so an interface may declare only its `type`, and an empty `interfaces` array still
validates.

#### Scenario: Part with physical interface
- **WHEN** a part has a USB-C port cutout
- **THEN** its `interfaces` array contains an entry with `type: "port_cutout"`, `connector: "usb_c"`, `wall`, and `position_mm`

#### Scenario: Interface with structured placement is machine-readable
- **WHEN** an interface entry declares `position_mm` and a size field
- **THEN** the schema validates them as structured fields (an array of numbers for `position_mm`, a number or `[w, h]` for the size), rejecting a malformed placement

#### Scenario: Interface with only a type still validates
- **WHEN** an interface entry declares `type` but no `wall`, `position_mm`, or size
- **THEN** validation passes (the placement fields are optional)

#### Scenario: Part with no interfaces
- **WHEN** a part is a simple bracket with no connectors or mating surfaces
- **THEN** its `interfaces` array is empty and validation still passes

#### Scenario: Multi-part plan needs no assembly object
- **WHEN** a plan contains two or more parts
- **THEN** validation passes without an `assembly` field, and the schema rejects an `assembly` property if one is supplied

---

### Requirement: Plan is shown to user for review before loop starts
The system SHALL display the generated `BUILD_PLAN.json` to the user and pause for confirmation or edits before the orchestration loop begins.

A dimension-validation checkpoint SHALL occur before `BUILD_PLAN.json` is generated (see `dimension-validation-checkpoint` spec). Confirmation of that checkpoint does not substitute for review of the final plan -- both pauses are required.

The system SHALL write `BUILD_PLAN.json` to disk after validation passes, then display a human-readable Markdown summary of the plan to the user and pause for confirmation or edits before the orchestration loop begins. The path written to disk SHALL be shown alongside the summary. The raw JSON SHALL NOT be displayed in the chat; only the summary is shown.

The summary SHALL include the following sections:
- Printer, material, and nozzle diameter
- Parts table: ID, description, W x D x H dimensions, print orientation, and blocks_needed
- Interfaces table: one row per interface entry across all parts, showing part ID, type, connector (if any), wall, and position
- Constraints: wall_min_mm, overhang_max_deg, dimension_tolerance_mm

The summary SHALL NOT include an assembly-strategy section.

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

#### Scenario: Summary shows no assembly strategy
- **WHEN** the plan has more than one part
- **THEN** the summary contains no assembly-strategy section; multi-part relationships are conveyed by the parts table and their placements

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

### Requirement: Build plan carries a per-part load determined by the planner
The build plan SHALL allow a part to declare a `load`: the principal load direction (and
optional `type`) in the part's own authored frame, used to drive print-orientation strength
scoring. The planning phase SHALL determine and declare the principal load for every part
whose print orientation depends on strength -- naming the real load path rather than leaving
it to be guessed downstream -- and SHALL ask the user when the load path is genuinely unclear
rather than omitting the field. A flat cover, lid, or panel that carries no structural
tension/bending/shear load SHALL be declared with `load.type: "compression"` (orientation-
neutral) so it is not tipped onto its edge. Plan validation SHALL accept the field when
present (a direction in the authored frame) and SHALL still accept parts that omit it. When a
part declares `load`, the planning summary SHALL surface it. When a part omits `load`, the
downstream strength scoring SHALL be orientation-neutral (no load axis is inferred from
geometry); an omitted load is a neutral default, never a fabricated bending direction.

#### Scenario: Plan with a declared load validates
- **WHEN** a build plan declares a `load` direction on a part
- **THEN** plan validation accepts it and the value is available to the orientation
  optimizer

#### Scenario: Plan without a load is still valid and scores neutral
- **WHEN** a part omits the `load` field
- **THEN** plan validation accepts the part and downstream strength scoring is
  orientation-neutral for it (no geometry-inferred load axis is fabricated)

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

---

### Requirement: Planning phase surfaces cq_gears as an external resource when gears are needed

When the user's request or the resulting decomposition calls for gear geometry (e.g. a spur, helical, or other toothed gear, pinion, or gearbox part), and no block in `blocks_needed` provides gear geometry, the planning prompt SHALL note in `planning_notes` that `blocks/` has no gear block yet and point to `https://github.com/lwidm/cq_gears` as a downloadable external resource the user can install and use to generate the gear geometry themselves. This note SHALL NOT add a dependency, block, or schema field -- it is prose guidance surfaced to the user alongside the rest of `planning_notes`.

#### Scenario: Design includes a gear part

- **WHEN** the user's request describes a part that is a gear, pinion, or toothed gear component
- **THEN** the generated `BUILD_PLAN.json`'s `planning_notes` states that no gear block exists in the inventory and references `https://github.com/lwidm/cq_gears` as an external resource to generate the geometry

#### Scenario: Design has no gear parts

- **WHEN** the user's request contains no gear, pinion, or toothed-gear part
- **THEN** `planning_notes` contains no `cq_gears` reference

#### Scenario: Pointer does not add a dependency or block

- **WHEN** the gear pointer is surfaced in `planning_notes`
- **THEN** `pyproject.toml`, `blocks/inventory.json`, and the `BUILD_PLAN.json` schema are unaffected -- `blocks_needed` for the gear part is left empty or uses only inventory blocks, with the scratch-geometry rationale in `part_notes` as usual

---

### Requirement: Plan records an optional per-part archetype

The `BUILD_PLAN.json` schema SHALL define an optional per-part `archetype` field (string). `prompts/planning.md` SHALL instruct the planner to set it to the name of the matching entry in `templates/archetypes.json` when a part fits an archetype's `use` description, and to omit the field otherwise; the archetype index SHALL be made available to the planning prompt for this purpose. `plan_validate.py` SHALL cross-check every present `archetype` value against the names in `templates/archetypes.json`, reporting an unknown name as a validation error, exactly as `blocks_needed` is checked against the block inventory. Plans without any `archetype` fields SHALL remain valid.

#### Scenario: Planner records a matching archetype

- **WHEN** the planner produces a plan containing a part that fits the enclosure-body archetype
- **THEN** that part entry carries `archetype: "enclosure-body"` and the plan passes validation

#### Scenario: Unknown archetype name is rejected

- **WHEN** a plan declares `archetype: "no-such-shape"` on a part
- **THEN** `plan_validate.py` reports a validation error naming the part and the unknown archetype

#### Scenario: Plans without archetypes stay valid

- **WHEN** a plan (including any pre-existing plan) declares no `archetype` field on any part
- **THEN** validation passes unchanged
