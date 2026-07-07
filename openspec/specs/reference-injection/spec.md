# Reference Injection

## Purpose

Defines requirements for how reference files (`CadQuery Pattern Reference.md`, `emboss_text.md`, and `FDM 3D Print Design Guidelines.md`) are loaded and injected into part and planning prompts.

## Requirements

### Requirement: CQ reference is injected into part prompts, text gotchas only for text parts
The system SHALL substitute `{{CQ_REFERENCE}}` in `prompts/part.md` with the full contents of `reference/CadQuery Pattern Reference.md` before each `claude -p` invocation, and SHALL append `reference/emboss_text.md` (after the pattern reference) ONLY when the part involves text/emboss — i.e. its `description`, `part_notes`, or any `interfaces` entry mentions text/engrave/emboss/label. A part with no text SHALL NOT receive `emboss_text.md` (the pattern reference already carries the basic `.text()` idiom). There SHALL be no `prompts/assembly.md`, so no assembly prompt receives the CQ reference.

#### Scenario: Part with no text gets the pattern reference only
- **WHEN** the part prompt is rendered for a part whose description, part_notes, and interfaces do not mention text/engrave/emboss/label
- **THEN** the rendered prompt contains the complete contents of `reference/CadQuery Pattern Reference.md` at the `{{CQ_REFERENCE}}` location and does NOT contain `reference/emboss_text.md`

#### Scenario: Text part gets the emboss gotchas appended
- **WHEN** the part prompt is rendered for a part that involves text/emboss
- **THEN** the rendered prompt contains `reference/CadQuery Pattern Reference.md` followed by the complete contents of `reference/emboss_text.md` at the `{{CQ_REFERENCE}}` location

#### Scenario: No assembly prompt to inject into
- **WHEN** the build pipeline reaches the assembly phase
- **THEN** there is no `prompts/assembly.md` template and no assembly-prompt CQ-reference substitution occurs

---

### Requirement: FDM guidelines are tag-filtered before injection
The system SHALL parse `<!-- applies_to: block1, block2 -->` tags from `reference/FDM 3D Print Design Guidelines.md` and inject only sections whose `applies_to` list intersects with the current `blocks_needed`, plus all sections tagged `always`.

#### Scenario: Part uses snap-fit blocks
- **WHEN** a part has `blocks_needed: ["snap_hook_clip"]`
- **THEN** the rendered part prompt includes the "Snap-fit Design" guideline section and all `always`-tagged sections, but excludes sections tagged for unrelated blocks

#### Scenario: Part uses no blocks
- **WHEN** a part has `blocks_needed: []`
- **THEN** the rendered part prompt includes only sections tagged `always`

#### Scenario: Malformed or missing tag
- **WHEN** a guideline section has no `<!-- applies_to: ... -->` comment
- **THEN** that section is excluded from all injections (not injected by default)

---

### Requirement: FDM guidelines placeholder substituted across all part blocks for planning
The system SHALL inject FDM guideline sections matching the union of all `blocks_needed` across all parts in the plan when substituting `{{FDM_GUIDELINES}}` in `prompts/planning.md`.

#### Scenario: Multi-part plan with different blocks per part
- **WHEN** the plan has `body` needing `["hollow_box"]` and `lid` needing `["snap_hook_clip"]`
- **THEN** the planning prompt includes guideline sections for both `hollow_box` and `snap_hook_clip`, plus all `always` sections

---

### Requirement: Reference files are loaded once per build, not per part
The system SHALL load reference file content once at the start of `build()` and reuse the loaded content for all part prompts in the same build.

#### Scenario: Three-part build
- **WHEN** the build plan contains three parts
- **THEN** `reference/CadQuery Pattern Reference.md` and `reference/emboss_text.md` are each read from disk exactly once during the build, not three times
