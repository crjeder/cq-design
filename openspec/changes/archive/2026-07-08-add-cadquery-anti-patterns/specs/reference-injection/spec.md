## MODIFIED Requirements

### Requirement: CQ reference is injected into part prompts, text gotchas only for text parts
The system SHALL substitute `{{CQ_REFERENCE}}` in `prompts/part.md` with the full contents of `reference/CadQuery Pattern Reference.md` followed by the full contents of `reference/CadQuery Anti-Patterns.md` before each `claude -p` invocation, and SHALL append `reference/emboss_text.md` (after the anti-patterns companion) ONLY when the part involves text/emboss — i.e. its `description`, `part_notes`, or any `interfaces` entry mentions text/engrave/emboss/label. The anti-patterns companion SHALL be injected unconditionally for every part (it is not gated on any part attribute); a part with no text SHALL NOT receive `emboss_text.md` (the pattern reference already carries the basic `.text()` idiom). There SHALL be no `prompts/assembly.md`, so no assembly prompt receives the CQ reference.

#### Scenario: Part with no text gets pattern reference plus anti-patterns
- **WHEN** the part prompt is rendered for a part whose description, part_notes, and interfaces do not mention text/engrave/emboss/label
- **THEN** the rendered prompt contains the complete contents of `reference/CadQuery Pattern Reference.md` followed by the complete contents of `reference/CadQuery Anti-Patterns.md` at the `{{CQ_REFERENCE}}` location, and does NOT contain `reference/emboss_text.md`

#### Scenario: Text part gets pattern reference, anti-patterns, then emboss gotchas
- **WHEN** the part prompt is rendered for a part that involves text/emboss
- **THEN** the rendered prompt contains `reference/CadQuery Pattern Reference.md`, followed by `reference/CadQuery Anti-Patterns.md`, followed by the complete contents of `reference/emboss_text.md` at the `{{CQ_REFERENCE}}` location

#### Scenario: Anti-patterns companion is always present
- **WHEN** the part prompt is rendered for any part, regardless of its blocks, interfaces, or description
- **THEN** the rendered prompt contains the complete contents of `reference/CadQuery Anti-Patterns.md`

#### Scenario: No assembly prompt to inject into
- **WHEN** the build pipeline reaches the assembly phase
- **THEN** there is no `prompts/assembly.md` template and no assembly-prompt CQ-reference substitution occurs
