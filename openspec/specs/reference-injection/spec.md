# Reference Injection

## Purpose

Defines requirements for how reference files (`CadQuery Pattern Reference.md` and `FDM 3D Print Design Guidelines.md`) are loaded and injected into part, assembly, and planning prompts.

## Requirements

### Requirement: CQ reference is injected in full into part and assembly prompts
The system SHALL load `reference/CadQuery Pattern Reference.md` once per build and substitute it for `{{CQ_REFERENCE}}` in `prompts/part.md` and `prompts/assembly.md` before each `claude -p` invocation.

#### Scenario: Part prompt contains full CQ reference
- **WHEN** `_render_part_prompt` is called for any part
- **THEN** the rendered prompt contains the complete contents of `reference/CadQuery Pattern Reference.md` at the `{{CQ_REFERENCE}}` location

#### Scenario: Assembly prompt contains full CQ reference
- **WHEN** `_render_assembly_prompt` is called
- **THEN** the rendered prompt contains the complete contents of `reference/CadQuery Pattern Reference.md` at the `{{CQ_REFERENCE}}` location

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
The system SHALL load reference file content once at the start of `build()` and reuse the loaded content for all part and assembly prompts in the same build.

#### Scenario: Three-part build
- **WHEN** the build plan contains three parts
- **THEN** `reference/CadQuery Pattern Reference.md` is read from disk exactly once during the build, not three times
