## MODIFIED Requirements

### Requirement: CQ reference is injected into part prompts, text gotchas only for text parts
The system SHALL resolve `{{CQ_REFERENCE}}` in `prompts/part.md` by rendering mode.
For an **inline render** (the orchestrating Claude authors the part in its own
context), the placeholder SHALL be substituted with a citation block that
names `reference/CadQuery Pattern Reference.md` and
`reference/CadQuery Anti-Patterns.md` as already-in-context documents to
apply, and SHALL NOT duplicate their contents; the citation SHALL name
`reference/emboss_text.md` ONLY when the part involves text/emboss - i.e. its
`description`, `part_notes`, or any `interfaces` entry mentions
text/engrave/emboss/label. For a **cold-context render** (a `claude -p`
subprocess or a subagent), the placeholder SHALL be substituted with the
selected sections' full text from `reference/CadQuery Pattern Reference.md`
followed by the selected sections' full text from
`reference/CadQuery Anti-Patterns.md`, appending `reference/emboss_text.md`
(after the anti-patterns companion) ONLY for text/emboss parts. There SHALL
be no `prompts/assembly.md`, so no assembly prompt receives the CQ reference.

**Note:** `render_prompt.py builder` has one rendering path (used for both a
spawned agent and the `"inline"`-routed orchestrator, per
`skill/phase3_build.md`'s "Do not read reference documents ... into this
session for the agents' sake" - the orchestrator reads the same rendered
file rather than holding these documents in its own context either way).
This requirement's inline/cold-context split describes the citation contract
as written before this change and is unmodified here; only the cold-context
substitution's *content* (full files -> tag-selected sections) changes in
this change. Reconciling the inline branch with actual `render_prompt.py`
behavior is out of scope for this change.

#### Scenario: Inline render cites instead of pasting
- **WHEN** the part prompt is rendered inline for any part
- **THEN** the rendered prompt names the two documents at the
  `{{CQ_REFERENCE}}` location and does NOT contain the body text of either
  document

#### Scenario: Inline render for a text part cites emboss gotchas
- **WHEN** the part prompt is rendered inline for a part that involves text/emboss
- **THEN** the citation block additionally names `reference/emboss_text.md`

#### Scenario: Cold-context render gets the selected sections' full contents
- **WHEN** the part prompt is rendered for a `claude -p` subprocess or a subagent
- **THEN** the rendered prompt contains the full text of the sections selected
  (per the tag-filtering requirement below) from
  `reference/CadQuery Pattern Reference.md` followed by the selected sections
  of `reference/CadQuery Anti-Patterns.md` at the `{{CQ_REFERENCE}}` location,
  plus `reference/emboss_text.md` for text/emboss parts only

#### Scenario: No assembly prompt to inject into
- **WHEN** the build pipeline reaches the assembly phase
- **THEN** there is no `prompts/assembly.md` template and no assembly-prompt
  CQ-reference substitution occurs

---

## ADDED Requirements

### Requirement: CQ reference sections are tag-filtered like the FDM and Engineering guides

The system SHALL parse `<!-- applies_to: block1, block2 -->` / `always` tags
from `reference/CadQuery Pattern Reference.md` and
`reference/CadQuery Anti-Patterns.md`, using the same tag vocabulary and
`tagged_sections()` selection rule already used for `{{FDM_GUIDELINES}}` and
`{{ENGINEERING_RULES}}`. Selection for a part SHALL intersect each document's
`applies_to` tags with the union of the part's `blocks_needed` and the
following feature-derived tags, computed the same way the existing
text/emboss detection (`TEXT_RE`) already is:

- `adv3d` - the part's `description`, `part_notes`, or any `interfaces` entry
  mentions revolve/loft/sweep/twist
- `multi_union` - the part declares more than one entry in `unions`

(No `text` tag is introduced: `reference/emboss_text.md` already handles the
text/emboss case as its own always-appended-when-relevant file, outside this
tag system, and no `CadQuery Pattern Reference.md`/`CadQuery Anti-Patterns.md`
section is text-specific enough to warrant one.)

An untagged `##` section SHALL be excluded from all selections, matching the
FDM/Engineering behavior.

#### Scenario: Simple box part selects only always-tagged sections
- **WHEN** a part with `blocks_needed: []`, `unions: null`, and a description
  containing no text/revolve/loft/sweep/twist language is rendered
- **THEN** only sections tagged `always` in `CadQuery Pattern Reference.md`
  and `CadQuery Anti-Patterns.md` are selected

#### Scenario: Part mentioning a revolved profile selects the adv3d section
- **WHEN** a part's `description` mentions "revolve this profile around the
  Z axis"
- **THEN** the "Advanced 3D Operations (Loft, Sweep, Revolve)" section of
  `CadQuery Pattern Reference.md` is selected in addition to `always` sections

#### Scenario: Multi-union part selects the compound-assembly section
- **WHEN** a part's `unions` array has more than one entry
- **THEN** the "Non-Overlapping Part Assembly (Performance)" section of
  `CadQuery Pattern Reference.md` is selected in addition to `always` sections

#### Scenario: Part with a block-tagged section
- **WHEN** a part's `blocks_needed` intersects a section's `applies_to` list
- **THEN** that section is selected in addition to `always` sections

#### Scenario: Malformed or missing tag
- **WHEN** a `##` section in either document has no
  `<!-- applies_to: ... -->` comment
- **THEN** that section is excluded from all selections

---

### Requirement: An anti-pattern already caught by a mechanical script_lint check may drop its prose

An `CadQuery Anti-Patterns.md` section MAY be removed, independent of the
existing non-recallable-content and attempt-history-evidence rules, when both
hold: (1) `script_lint.py` already detects the exact mistake the section
describes and returns a typed finding whose `hint` states the fix, and (2)
the section's content is a duplicate of prose already retained elsewhere in
`reference/CadQuery Pattern Reference.md` (so the underlying mechanism is
still taught once). A section satisfying only one of these two conditions
SHALL be retained.

#### Scenario: Duplicate section with mechanical coverage is removed
- **WHEN** an Anti-Patterns section's mistake is a `script_lint.py` finding
  type AND the same mechanism is explained in the Pattern Reference document
- **THEN** the Anti-Patterns section is removed and the Pattern Reference
  section is retained as the sole explanation

#### Scenario: Mechanically-caught mistake with no duplicate explanation is retained
- **WHEN** an Anti-Patterns section's mistake is a `script_lint.py` finding
  type but no other retained document explains the underlying mechanism
- **THEN** the section is retained

#### Scenario: Undetected mistake is retained regardless of duplication
- **WHEN** an Anti-Patterns section describes a mistake `script_lint.py` does
  not detect
- **THEN** the section is retained even if it overlaps another document's
  explanation
