# Reference Injection

## Purpose

Defines requirements for how reference files (`CadQuery Pattern Reference.md`, `emboss_text.md`, and `FDM 3D Print Design Guidelines.md`) are loaded and injected into part and planning prompts.

## Requirements

### Requirement: CQ reference is injected into part prompts, text gotchas only for text parts
The system SHALL resolve `{{CQ_REFERENCE}}` in `prompts/part.md` by rendering mode.
For an **inline render** (the orchestrating Claude authors the part in its own
context), the placeholder SHALL be substituted with a citation block that names
`reference/CadQuery Pattern Reference.md` and `reference/CadQuery Anti-Patterns.md`
as already-in-context documents to apply, and SHALL NOT duplicate their contents;
the citation SHALL name `reference/emboss_text.md` ONLY when the part involves
text/emboss - i.e. its `description`, `part_notes`, or any `interfaces` entry
mentions text/engrave/emboss/label. For a **cold-context render** (a `claude -p`
subprocess or a subagent), the placeholder SHALL be substituted with the full
contents of `reference/CadQuery Pattern Reference.md` followed by the full contents
of `reference/CadQuery Anti-Patterns.md`, appending `reference/emboss_text.md`
(after the anti-patterns companion) ONLY for text/emboss parts. The anti-patterns
companion SHALL be cited (inline) or injected (cold) unconditionally for every
part; a part with no text SHALL NOT receive or cite `emboss_text.md` (the pattern
reference already carries the basic `.text()` idiom). There SHALL be no
`prompts/assembly.md`, so no assembly prompt receives the CQ reference.

#### Scenario: Inline render cites instead of pasting
- **WHEN** the part prompt is rendered inline for any part
- **THEN** the rendered prompt names `reference/CadQuery Pattern Reference.md` and
  `reference/CadQuery Anti-Patterns.md` at the `{{CQ_REFERENCE}}` location and does
  NOT contain the body text of either document

#### Scenario: Inline render for a text part cites emboss gotchas
- **WHEN** the part prompt is rendered inline for a part that involves text/emboss
- **THEN** the citation block additionally names `reference/emboss_text.md`

#### Scenario: Cold-context render gets full contents
- **WHEN** the part prompt is rendered for a `claude -p` subprocess or a subagent
- **THEN** the rendered prompt contains the complete contents of
  `reference/CadQuery Pattern Reference.md` followed by the complete contents of
  `reference/CadQuery Anti-Patterns.md` at the `{{CQ_REFERENCE}}` location, plus
  `reference/emboss_text.md` for text/emboss parts only

#### Scenario: Anti-patterns companion is always present in some form
- **WHEN** the part prompt is rendered for any part in either mode
- **THEN** the prompt cites (inline) or contains (cold) the anti-patterns
  companion

#### Scenario: No assembly prompt to inject into
- **WHEN** the build pipeline reaches the assembly phase
- **THEN** there is no `prompts/assembly.md` template and no assembly-prompt
  CQ-reference substitution occurs

---

### Requirement: FDM guidelines are tag-filtered before injection
The system SHALL parse `<!-- applies_to: block1, block2 -->` tags from
`reference/FDM 3D Print Design Guidelines.md` and select only sections whose
`applies_to` list intersects with the current `blocks_needed`, plus all sections
tagged `always`. For a cold-context part render the selected sections' full text
SHALL be injected at `{{FDM_GUIDELINES}}`; for an inline part render the
`{{FDM_GUIDELINES}}` value SHALL be the list of selected section names (as a
citation into the already-in-context guide), not their bodies.

#### Scenario: Part uses snap-fit blocks (cold context)
- **WHEN** a part with `blocks_needed: ["snap_hook_clip"]` is rendered for a cold
  context
- **THEN** the rendered part prompt includes the "Snap-fit Design" guideline
  section body and all `always`-tagged sections, but excludes sections tagged for
  unrelated blocks

#### Scenario: Part uses snap-fit blocks (inline)
- **WHEN** the same part is rendered inline
- **THEN** the rendered prompt lists "Snap-fit Design" and the `always`-tagged
  section names at the `{{FDM_GUIDELINES}}` location without their body text

#### Scenario: Part uses no blocks
- **WHEN** a part has `blocks_needed: []`
- **THEN** the selection contains only sections tagged `always`, cited by name
  inline or injected in full for a cold context

#### Scenario: Malformed or missing tag
- **WHEN** a guideline section has no `<!-- applies_to: ... -->` comment
- **THEN** that section is excluded from all selections (not selected by default)

---

### Requirement: Engineering design rules are tag-filtered and mode-rendered like the FDM guide

There SHALL be a `reference/Engineering Design Rules.md` containing only numeric
engineering content - material constants (allowable strain, flexural modulus per
material), snap-fit formula coefficients, rib/boss/gusset ratio limits, insert and
clearance deltas not already in `hardware_dims.md` - with no prose tutorials, using
`<!-- applies_to: block1, block2 -->` section tags with the same vocabulary as the
FDM guide (including `always` for material constants). Section selection for a part
SHALL intersect `applies_to` with the part's `blocks_needed` plus `always`-tagged
sections, and SHALL additionally select all load-relevant sections when the part
declares a plan `load`. Rendering SHALL follow the existing mode split: an inline
part render cites the selected section names as already-in-context material; a
cold-context render (subagent or `claude -p`) receives the selected sections' full
bodies. An untagged section SHALL be excluded from all selections.

#### Scenario: Snap-fit part in a cold context

- **WHEN** a part with `blocks_needed: ["snap_hook_clip"]` is rendered for a cold
  context
- **THEN** the rendered prompt contains the snap-fit coefficient section body and
  all `always`-tagged constant sections, and excludes sections tagged only for
  unrelated blocks

#### Scenario: Same part rendered inline

- **WHEN** the same part is rendered inline
- **THEN** the prompt cites the selected section names of
  `reference/Engineering Design Rules.md` without their bodies

#### Scenario: Part with a declared load but no tagged blocks

- **WHEN** a part declares `load` in its plan entry and uses no load-bearing blocks
- **THEN** the load-relevant sections are still selected for it, plus `always`
  sections

#### Scenario: Non-load-bearing part

- **WHEN** a part with no `load` and no matching block tags is rendered
- **THEN** only `always`-tagged sections are selected (cited inline, injected cold)

---

### Requirement: Inline citation requires the references in context
Inline citation rendering SHALL be valid only when the Phase 3 setup reads of the
cited documents happened in the current session context. When that cannot be
confirmed (e.g. a resumed or compacted session), the system SHALL re-read the
cited documents before the first inline part render.

#### Scenario: Fresh session after Phase 3 setup
- **WHEN** Phase 3 setup read the pattern reference, anti-patterns, and FDM guide
  and the part loop starts in the same session
- **THEN** inline part prompts use citation substitution

#### Scenario: Resumed session without visible setup reads
- **WHEN** the part loop starts in a session where the setup reads are not in the
  visible context
- **THEN** the documents are re-read before the first part prompt is rendered
  inline

### Requirement: Retry renders inherit the rendering mode
A retry prompt for a failed attempt SHALL use the same rendering mode as the
original attempt's context: inline retries cite, cold-context retries receive full
substitution.

#### Scenario: Inline part-loop retry
- **WHEN** an inline attempt fails and the part loop builds a correction prompt
- **THEN** the correction prompt cites the references and does not re-paste them

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
