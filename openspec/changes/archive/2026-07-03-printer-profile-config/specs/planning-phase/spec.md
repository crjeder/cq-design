## MODIFIED Requirements

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
