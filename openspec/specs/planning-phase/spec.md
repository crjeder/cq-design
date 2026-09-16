# Planning Phase

## Purpose

Defines requirements for the planning phase: the prompt that produces `BUILD_PLAN.json` and the schema that file must conform to.

## Requirements

### Requirement: Planning prompt produces structured BUILD_PLAN
The system SHALL provide a `prompts/planning.md` prompt that, when invoked with a user's model description and rendered with `{{USER_REQUEST}}`, `{{BLOCK_INVENTORY}}`, `{{ARCHETYPE_INDEX}}`, `{{FDM_GUIDELINES}}`, and `{{PRINTER_PROFILE}}`, produces a valid `BUILD_PLAN.json` file conforming to the defined schema. All placeholder substitution SHALL be performed by `src/render_prompt.py planning` before invoking the LLM (see `planner-research-prompt-rendering` spec), not by hand in the main session and not by `orchestrate.py`.

The `{{FDM_GUIDELINES}}` placeholder SHALL be substituted with sections from `reference/FDM 3D Print Design Guidelines.md` tagged `always`, plus, on a re-plan where the prior `BUILD_PLAN.json` is passed, sections matching the union of all `blocks_needed` across all parts in that plan.

The `{{PRINTER_PROFILE}}` placeholder SHALL be substituted with the resolved `printer`, `material`, `nozzle_mm`, and `constraints` values from a validated `printer_profile.json` in the working directory, when one exists (see `printer-profile-config` spec). When `printer_profile.json` is absent or fails validation, the corresponding field(s) SHALL instead be asked of the user, exactly as when no profile exists.

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
each part's `placement`, which the part author supplies during the build phase (see
`assembled-pose-handback`); the planner expresses the same relationship as each part's
`pose_intent`.

Each part object SHALL include:
- `id` (string, required, unique)
- `description` (string, required)
- `dimensions` (object with `w_mm`, `d_mm`, `h_mm`, required)
- `interfaces` (array, may be empty)
- `blocks_needed` (array of block names from inventory, may be empty)
- `print_orientation` (string, required)
- `pose_intent` (string, optional): the part's goal pose in the shared assembled frame,
  stated as intent rather than as a rotation sequence

Each `interfaces[]` entry SHALL require `type` (string) and MAY carry structured,
machine-readable placement fields (all optional): `name` (the agreed vocabulary word for
the feature), `wall` (one of the six face names), `position_mm` (`[x, y, z]`, the
feature's intended center in the part's authored frame), and a size field
(`diameter_mm` for round features, or `size_mm` as `[w, h]` for rectangular). These
fields SHALL be defined in the schema (not free-form `additionalProperties`), so a
declared placement is machine-readable; they remain optional so an interface may declare
only its `type`, and an empty `interfaces` array still validates.

The `name` field SHALL be constrained to the same normalized snake_case form as a part
`id` (`^[a-z][a-z0-9_]*$`), so that the mechanical normalization promised by the
user-noun naming rule is enforced by the schema rather than left to the planner.

#### Scenario: Part with physical interface
- **WHEN** a part has a USB-C port cutout
- **THEN** its `interfaces` array contains an entry with `type: "port_cutout"`, `connector: "usb_c"`, `wall`, and `position_mm`

#### Scenario: Interface with structured placement is machine-readable
- **WHEN** an interface entry declares `position_mm` and a size field
- **THEN** the schema validates them as structured fields (an array of numbers for `position_mm`, a number or `[w, h]` for the size), rejecting a malformed placement

#### Scenario: Named interface validates
- **WHEN** an interface entry declares `name: "inner_lip"` alongside its `type`
- **THEN** validation passes and the name is available to downstream consumers as a structured field

#### Scenario: Non-normalized interface name is rejected
- **WHEN** an interface entry declares `name: "Inner Lip"` or `name: "inner-lip"`
- **THEN** validation fails with a schema error naming the offending field, rather than silently accepting an unnormalized vocabulary word

#### Scenario: Interface with only a type still validates
- **WHEN** an interface entry declares `type` but no `name`, `wall`, `position_mm`, or size
- **THEN** validation passes (the placement fields are optional)

#### Scenario: Part with no interfaces
- **WHEN** a part is a simple bracket with no connectors or mating surfaces
- **THEN** its `interfaces` array is empty and validation still passes

#### Scenario: Multi-part plan needs no assembly object
- **WHEN** a plan contains two or more parts
- **THEN** validation passes without an `assembly` field, and the schema rejects an `assembly` property if one is supplied

#### Scenario: Part declares its pose as intent
- **WHEN** a planner positions a part away from the assembled-frame origin
- **THEN** the part carries a `pose_intent` string and no planner-written `placement`

#### Scenario: Plan without pose intent still validates
- **WHEN** a part declares neither `pose_intent` nor `placement`
- **THEN** validation passes; the part is treated as authored in the assembled frame

---

### Requirement: Planning consumes the approved intent rather than authoring it

The planning phase SHALL treat the approved reformulation Phase 1 wrote to `intent` as
input: it SHALL copy that text into the emitted `BUILD_PLAN.json`'s `intent` unchanged,
and SHALL plan the part decomposition against it. The planner SHALL NOT author `intent`
from scratch, and SHALL NOT paraphrase or shorten the approved text.

When a re-plan regenerates the file, the planner SHALL carry the current approved
`intent` forward unchanged, the same way it carries `request_log` forward. Only an
approved correction rewrites `intent` (see the `approved-intent` spec).

#### Scenario: Planner copies the approved intent

- **WHEN** Phase 1 exits with an approved reformulation and the planner is invoked
- **THEN** the emitted `BUILD_PLAN.json` carries that text verbatim as `intent`

#### Scenario: Re-plan preserves the approved intent

- **WHEN** a correction causes the planner to regenerate the plan
- **THEN** the new `BUILD_PLAN.json` carries forward the current approved `intent`, and
  the planner does not rewrite it

#### Scenario: Plan contradicts the approved intent

- **WHEN** the decomposition the planner produces would build something the approved
  `intent` does not describe
- **THEN** the planner revises the decomposition to match the approved intent rather than
  editing `intent` to match the decomposition

### Requirement: Plan validation rejects a token intent

The `BUILD_PLAN.json` schema SHALL require `intent` to be long enough to carry a
reformulation rather than a token phrase, so that a plan whose `intent` was never
replaced by the Phase 1 approved text fails validation.

The `-1` unresolved-dimension placeholder needs no additional validator rule: every
size-valued numeric field in the schema (`parts[].dimensions.*`,
`interfaces[].diameter_mm`, `interfaces[].size_mm[]`, `blocks_needed[].extents_mm[]`,
`kinematics.step`) already carries `exclusiveMinimum: 0` and rejects it. The schema's
remaining unbounded numeric fields are signed by design -- `interfaces[].position_mm`,
`load.dir`, `show_face.dir`, `placement.translate_mm`, `placement.rotate[].angle_deg`,
`kinematics.axis_origin_mm`, `kinematics.required_range`, `kinematics.mechanical_limit`
-- where `-1` is a legitimate value. A blanket `-1` rejection SHALL NOT be added, as it
would reject valid plans.

#### Scenario: Token intent is rejected

- **WHEN** a plan's `intent` is shorter than the reformulation floor
- **THEN** `plan_validate.py` reports a schema validation error for `intent`

#### Scenario: Unresolved dimension is already rejected

- **WHEN** a part's `dimensions.d_mm` is `-1`
- **THEN** validation fails on the existing `exclusiveMinimum: 0` bound, naming that
  field

#### Scenario: A legitimate negative value still validates

- **WHEN** a part declares `load.dir` of `[0, 0, -1]` and an interface at
  `position_mm` `[-12.5, 0, 4]`
- **THEN** validation passes -- no rule rejects `-1` in a signed field

---

### Requirement: Interface names are unique within a part
`plan_validate.py` SHALL reject a plan in which two `interfaces[]` entries of the same
part declare the same `name`, mirroring the existing union-id uniqueness cross-check.
The error SHALL name the part and the duplicated name. Because callout badges are
numbered by supply order and the legend echoes names verbatim, a duplicate name within
one part would produce two indistinguishable legend lines and an ambiguous conversational
reference. Names SHALL be permitted to repeat across different parts, where the part id
disambiguates them.

#### Scenario: Duplicate name within one part is rejected
- **WHEN** a part declares two interfaces both named `mount_hole`
- **THEN** validation fails with an error naming that part and the duplicated name

#### Scenario: Same name on two different parts is accepted
- **WHEN** two different parts each declare an interface named `mount_hole`
- **THEN** validation passes

#### Scenario: Unnamed interfaces do not collide
- **WHEN** a part declares three interfaces, none of which carries a `name`
- **THEN** validation passes (the uniqueness check considers only declared names)

---

### Requirement: The plan summary shows each part's pose intent

The human-readable plan summary shown at the Phase 2 review checkpoint SHALL surface
each part's `pose_intent`, so the user reviews the assembled arrangement in the terms
the planner stated it. The summary SHALL NOT render rotation sequences or translation
vectors for parts.

#### Scenario: Summary shows the arrangement
- **WHEN** a multi-part plan is summarized for review
- **THEN** each part's row or entry carries its `pose_intent` text, and no `rotate`/
  `translate_mm` values appear in the summary

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

### Requirement: Build plan carries a review-policy preference

The build plan SHALL allow the user's review-frequency preference to be recorded
as a plan-level `review_policy` field, one of `minimal`, `checkpoints`, or
`every_stage`. Plan validation SHALL accept the field when present and SHALL
accept plans that omit it. The effective `review_policy` for a plan SHALL be its
own declared value when present, otherwise `every_stage`. The planning phase
SHALL record the policy from the user's stated review-frequency preference when
one is given, and the plan summary (see the "Plan is shown to user for review
before loop starts" requirement) SHALL surface the effective value.

`review_policy` replaces the previously informal, undeclared "run autonomously"
override as the mechanism for skipping progressive-build checkpoints -- see the
`progressive-build` spec for how the effective value selects build mode per part.

#### Scenario: Plan-level review policy validates

- **WHEN** a build plan declares `review_policy: "minimal"` at the plan level
- **THEN** plan validation accepts it and the value is available to the Phase 3
  part loop to select build mode

#### Scenario: Plan without a review policy defaults to every_stage

- **WHEN** a plan omits `review_policy` entirely
- **THEN** plan validation accepts it and the plan's effective review policy is
  `every_stage`

#### Scenario: Invalid review policy value is rejected

- **WHEN** a plan declares `review_policy` set to a value other than `minimal`,
  `checkpoints`, or `every_stage`
- **THEN** plan validation fails with an error naming the field and the invalid
  value

#### Scenario: Summary surfaces the effective review policy

- **WHEN** the plan summary is shown to the user before the orchestration loop
  starts
- **THEN** the summary states the plan's effective `review_policy`, whether
  declared explicitly or defaulted

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

---

### Requirement: Plan names reuse the user's own nouns

When the user has named a part or feature in their request or during the
conversation, `prompts/planning.md` SHALL instruct the planner to use that word as the
corresponding part `id` or `interfaces[].name`, normalized only mechanically
(lowercased, spaces and hyphens to underscores) -- never replaced by a synonym. The
planner SHALL coin names only for parts and features the user never named. Every coined
name SHALL be introduced to the user before the build loop starts via `plan_summary.py`'s
**Names I chose** section (see `plan-summary-checkpoint` spec), which detects a coined
name automatically by checking each part id and interface name against `request_log`
rather than requiring the reviewing session to spot it by reading `planning_notes`. When
normalization produces a collision with an existing id, the planner SHALL disambiguate
with a suffix and surface the rename in the summary.

#### Scenario: User noun becomes the plan name

- **WHEN** the user's request says "a mug with a handle"
- **THEN** the plan's interface or part representing that feature is named `handle`,
  not a planner-chosen synonym such as `grip` or `side_loop`

#### Scenario: Coined names are introduced at the checkpoint

- **WHEN** the plan contains a part the user never named
- **THEN** `plan_summary.py`'s **Names I chose** section lists that part's id before the
  user is asked to approve the plan

#### Scenario: Colliding user nouns are disambiguated visibly

- **WHEN** the user names two distinct features with the same word
- **THEN** the plan disambiguates them with suffixes and the plan summary states the
  mapping (in `planning_notes`, surfaced at the checkpoint), rather than silently
  renaming one

---

### Requirement: Plans derived from found sources record provenance

When a `BUILD_PLAN.json` derives from a source found during Phase 0 sourcing
triage (a reused/converted parametric source, an imported BREP, or a rung-4
partial rebuild), `prompts/planning.md` SHALL instruct that `planning_notes`
records the source URL, the license, and the sourcing rung under which it was
reused. Plans for from-scratch designs (rung 5 or Phase 0 skipped) are
unaffected.

#### Scenario: Rung 4 partial rebuild plan

- **WHEN** planning runs for a part rebuilt from a close-fit found mesh
- **THEN** the resulting `BUILD_PLAN.json`'s `planning_notes` contains the
  found model's URL, its license, and the rung

#### Scenario: From-scratch plan

- **WHEN** planning runs for a request where Phase 0 found nothing usable
- **THEN** no provenance entry is required in `planning_notes`

---

### Requirement: Planning prompt rules are uniquely numbered

`prompts/planning.md`'s Rules section SHALL assign each rule a unique identifier
(a bare number, or a number with a lettered suffix such as `3a`), with no two rules
sharing the same identifier. Other documents in the repository (e.g.
`skill/phase2_planning.md`, `skill/phase3_build.md`) cite specific rules by this
identifier; a duplicate identifier makes such a citation ambiguous.

#### Scenario: No duplicate rule identifiers

- **WHEN** `prompts/planning.md`'s Rules section is scanned for its rule identifiers
- **THEN** every identifier appears exactly once

#### Scenario: Cross-referenced rule identifiers stay resolvable

- **WHEN** another document in the repository cites a `prompts/planning.md` rule by
  number (e.g. "rule 14")
- **THEN** exactly one rule in the current `prompts/planning.md` carries that
  identifier, and its subject matter matches what the citing document describes

---

### Requirement: planning_notes carries only three categories of content
`prompts/planning.md` SHALL bound `planning_notes` by an inclusion rule rather than
commissioning general design reasoning. The field SHALL carry only:

- **(a) Decisions against something**, with the reason: a rejected alternative design, a
  rejected archetype, a schema mechanism that cannot express the design, a deviation
  from the user's literal request, a deviation from a `printer_profile.json` default, or
  an optional field deliberately left empty. Where a rejection forces a compensating
  measure, the compensation is part of the record.
- **(b) Invariants binding more than one part**, which no per-part field can hold: the
  semantic anchors of the shared coordinate frame, a dimension in one part fixed by a
  feature of another, an authoring-frame convention that several parts must share, and
  the reason the parts must agree.
- **(c) The assembly procedure and the non-printed hardware it consumes**: the order and
  direction in which printed parts are put together, which features exist to serve
  assembly access rather than function, and any item the user must supply (rod, screw,
  insert, magnet, adhesive).

`prompts/planning.md` SHALL state that content outside these three categories does not
belong in `planning_notes`.

#### Scenario: A deliberately omitted optional field is recorded with its reason
- **WHEN** the planner leaves an optional field (for example a part's `load`, or a
  `kinematics` entry) empty on purpose
- **THEN** `planning_notes` records what was omitted and why, since no other field in the
  plan can express an absence

#### Scenario: A cross-part invariant is recorded once, not per part
- **WHEN** two or more parts must share a convention or a coordinate for the assembly to
  work (a shared authoring frame, a coordinate in one part fixed by another part's
  feature)
- **THEN** the invariant and the reason the parts must agree are stated in
  `planning_notes`, not split across each part's `part_notes` where the cross-part
  reason has no home

#### Scenario: Assembly procedure and supplied hardware are recorded
- **WHEN** the model requires the user to supply a non-printed item, or requires the
  printed parts to be assembled in a particular order or direction
- **THEN** `planning_notes` states the procedure and names the supplied item, including
  any feature that exists only to give the assembly step access

#### Scenario: Content outside the three categories is excluded
- **WHEN** the planner has reasoning that fits none of the three categories (for example
  a summary of DFM cleanup already visible in the parts, or per-part orientation
  rationale already in that part's `part_notes`)
- **THEN** it is omitted from `planning_notes`

---

### Requirement: planning_notes does not restate structured fields in prose
`prompts/planning.md` SHALL instruct that any fact already expressed by a structured
field of `BUILD_PLAN.json` -- including `placement`, `pose_intent`, `load`,
`dimensions`, `blocks_needed`, `interfaces`, `intent`, and `optimize_for` -- SHALL NOT
be narrated in `planning_notes`. The structured field is the single source. This
generalizes the existing `placement`-specific prohibition to every structured field.

#### Scenario: A part's declared load is not narrated
- **WHEN** a part declares a `load` object
- **THEN** `planning_notes` does not restate the load direction or type in prose; a
  cross-part consequence of that load remains admissible under category (b)

#### Scenario: Chosen blocks are not listed in prose
- **WHEN** parts declare `blocks_needed`
- **THEN** `planning_notes` does not enumerate which block was used for which feature,
  since `blocks_needed` already states it

---

### Requirement: A re-plan reads and rewrites planning_notes
`prompts/planning.md` SHALL instruct that on a re-plan (the planning agent running again
against an existing `BUILD_PLAN.json`) the agent reads the existing `planning_notes`
before re-deciding, does not silently re-litigate a decision recorded there, and
rewrites the field to describe the current state. Unlike `request_log`, `planning_notes`
is rewritten rather than carried forward entry by entry: superseded content is deleted,
and content still true is retained.

#### Scenario: A recorded rejection is not silently reversed
- **WHEN** a re-plan considers an approach that the existing `planning_notes` records as
  rejected
- **THEN** the agent either keeps the recorded decision, or adopts the approach and
  replaces the rejection record with the new decision and its reason -- never adopts it
  while leaving the stale rejection in place

#### Scenario: A superseded invariant is deleted, not annotated
- **WHEN** a re-plan changes a cross-part invariant recorded in `planning_notes`
- **THEN** the regenerated field states the new invariant and the superseded text is
  removed rather than annotated as superseded

---

### Requirement: planning_notes and part_notes describe current state only
`prompts/planning.md` and `prompts/part.md` SHALL instruct that `planning_notes`
(plan-level design reasoning, bounded by the three-category inclusion rule) and each
part's `part_notes` describe the CURRENT design state only -- decomposition choices,
dimension sources, blocks chosen, geometry rationale as of the present plan/script --
and SHALL NOT contain round-by-round build history, dated "ROUND N" narrative, or
"SUPERSEDED by round N" annotations. Round-by-round history belongs exclusively in
`request_log` (see the `request-log` capability).

#### Scenario: Part notes stay current-state-only across correction rounds
- **WHEN** a part's design changes across several correction rounds
- **THEN** its `part_notes` after each round describes only the design as it now
  stands, with no retained narrative from prior rounds

#### Scenario: Planning notes do not narrate the plan's revision history
- **WHEN** a plan is regenerated after a correction (a re-plan)
- **THEN** the regenerated `planning_notes` describes the current decomposition/
  reasoning, not a log of what changed from the previous plan version (that history is
  in `request_log`)

#### Scenario: A corrected decision is restated, not diffed
- **WHEN** a correction changes a decision recorded in `planning_notes`
- **THEN** the field states the decision as it now stands, without a
  "changed from X to Y this session" narrative
