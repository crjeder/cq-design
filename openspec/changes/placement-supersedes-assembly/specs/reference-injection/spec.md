## MODIFIED Requirements

### Requirement: CQ reference is injected in full into part and assembly prompts
The system SHALL load `reference/CadQuery Pattern Reference.md` once per build and substitute it for `{{CQ_REFERENCE}}` in `prompts/part.md` before each `claude -p` invocation. There SHALL be no `prompts/assembly.md`, so no assembly prompt receives the CQ reference.

#### Scenario: Part prompt contains full CQ reference
- **WHEN** `_render_part_prompt` is called for any part
- **THEN** the rendered prompt contains the complete contents of `reference/CadQuery Pattern Reference.md` at the `{{CQ_REFERENCE}}` location

#### Scenario: No assembly prompt to inject into
- **WHEN** the build pipeline reaches the assembly phase
- **THEN** there is no `prompts/assembly.md` template and no assembly-prompt CQ-reference substitution occurs

---

### Requirement: Reference files are loaded once per build, not per part
The system SHALL load reference file content once at the start of `build()` and reuse the loaded content for all part prompts in the same build.

#### Scenario: Three-part build
- **WHEN** the build plan contains three parts
- **THEN** `reference/CadQuery Pattern Reference.md` is read from disk exactly once during the build, not three times
