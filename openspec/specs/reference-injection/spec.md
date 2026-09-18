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
clearance deltas not already in `hardware_dims.md`, and the flush-fold hinge
standoff formula - with no prose tutorials, using `<!-- applies_to: block1,
block2 -->` section tags with the same vocabulary as the FDM guide (including
`always` for material constants). Section selection for a part SHALL intersect
`applies_to` with the part's `blocks_needed` plus `always`-tagged sections, SHALL
additionally select all load-relevant sections when the part declares a plan
`load`, and SHALL additionally select the flush-fold hinge section when any entry
in the plan's top-level `kinematics` array names this part as `moving_union`
(block-based or block-free). Rendering SHALL follow the existing mode split: an
inline part render cites the selected section names as already-in-context
material; a cold-context render (subagent or `claude -p`) receives the selected
sections' full bodies. An untagged section SHALL be excluded from all selections.

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

#### Scenario: Block-based hinge part

- **WHEN** a part with `blocks_needed: ["pin_hinge"]` (or `["living_hinge"]`) is
  rendered
- **THEN** the flush-fold hinge standoff section is selected, plus any
  `always`-tagged sections

#### Scenario: Block-free hinge part

- **WHEN** the plan's `kinematics` array has an entry naming this part as
  `moving_union` with no `block` reference (a raw-primitive hinge, per
  `blockless-kinematics`) and the part has no hinge-related `blocks_needed`
- **THEN** the flush-fold hinge standoff section is still selected for it, plus
  `always` sections

#### Scenario: Non-hinge part with no kinematics

- **WHEN** a part is named as `moving_union` in no `kinematics` entry and has no
  hinge-related `blocks_needed`
- **THEN** the flush-fold hinge standoff section is excluded

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
The system SHALL substitute `{{FDM_GUIDELINES}}` in `prompts/planning.md` with all
`planning`-tagged sections of `reference/FDM 3D Print Design Guidelines.md` plus, when a
prior `BUILD_PLAN.json` is passed to `render_prompt.py planning --plan`, the sections
matching the union of all `blocks_needed` across all parts in that plan. A fresh plan (no
prior plan) SHALL receive the `planning`-tagged sections only. The `planning` tag SHALL be
distinct from `always` (which continues to govern part/builder rendering unchanged): a
section MAY carry both tags when it is relevant to both phases.

#### Scenario: Multi-part plan with different blocks per part
- **WHEN** the prior plan has `body` needing `["hollow_box"]` and `lid` needing `["snap_hook_clip"]` and is passed via `--plan`
- **THEN** the planning prompt includes guideline sections for both `hollow_box` and `snap_hook_clip`, plus all `planning`-tagged sections

#### Scenario: Fresh plan
- **WHEN** `render_prompt.py planning` runs without `--plan`
- **THEN** the planning prompt includes only the `planning`-tagged FDM sections

#### Scenario: Section relevant to both phases
- **WHEN** a section is tagged `<!-- applies_to: always, planning -->`
- **THEN** it is selected for both the planner render and the builder/part render

#### Scenario: Builder rendering is unaffected
- **WHEN** a part prompt is rendered (inline or cold-context)
- **THEN** FDM section selection still uses the `always` tag plus block matches, unchanged from before this requirement's update

---

### Requirement: Reference files are loaded once per build, not per part
The system SHALL load reference file content once at the start of `build()` and reuse the loaded content for all part prompts in the same build.

#### Scenario: Three-part build
- **WHEN** the build plan contains three parts
- **THEN** `reference/CadQuery Pattern Reference.md` and `reference/emboss_text.md` are each read from disk exactly once during the build, not three times

---

### Requirement: Injected CadQuery references carry only non-recallable content

`reference/CadQuery Pattern Reference.md` and `reference/CadQuery Anti-Patterns.md`
SHALL contain only material a competent CadQuery author cannot reliably recall:
exact API signatures and argument semantics, selector-string vocabulary, OCC/BRep
failure signatures and their causes, numeric tables, and project-specific contracts
(block imports, `result` conventions, `cq_verify` usage). They SHALL NOT contain
prose tutorials, restatements of general Python or CAD fundamentals, or worked
examples whose idiom an archetype template in `templates/` already demonstrates.
Each document SHALL be at most 65% of its pre-change byte size.

#### Scenario: Tutorial prose is removed

- **WHEN** a section explains a general concept without naming an API signature, a
  failure signature, a numeric value, or a project contract
- **THEN** that section is absent from the condensed document

#### Scenario: Gotchas and tables are retained

- **WHEN** a section documents an exact API gotcha, an OCC error signature, or a
  numeric table
- **THEN** that section is retained in the condensed document

#### Scenario: Size target met

- **WHEN** the condensed documents are measured
- **THEN** each is at most 65% of its pre-change byte size

---

### Requirement: Reference cuts are backed by attempt-history evidence

A section removal SHALL be justified by evidence, not preference. Before removal,
the archived attempt telemetry (`build/attempts.jsonl` across `evals/runs/*`) SHALL
be surveyed for error types the section addresses. A section addressing an error
type observed in that history SHALL be retained (condensed, not deleted). The
evidence survey and the retain/cut decision per section SHALL be recorded in the
change's design document.

#### Scenario: Section maps to an observed error type

- **WHEN** a candidate section addresses an error type present in the archived
  attempt history
- **THEN** the section is retained in condensed form rather than removed

#### Scenario: Section maps to no observed error and no non-recallable content

- **WHEN** a candidate section addresses no observed error type and contains no
  signature, failure signature, table, or project contract
- **THEN** the section is removed

---

### Requirement: Condensation is validated by an eval sweep before acceptance

The condensed references SHALL be accepted only after a full eval sweep
(`evals/run_evals.py --generate` over the canonical corpus) whose first-shot rate
and attempts-to-pass are no worse than the preceding archived run, and whose mean
cold-render `prompt_chars` is measurably lower than the `c2-prompt-chars` run. A
sweep failing the first condition SHALL cause the condensation to be reverted or
narrowed, not accepted with a caveat.

#### Scenario: Sweep holds quality and reduces prompt size

- **WHEN** the post-condensation sweep holds first-shot rate and attempts-to-pass
  and shows lower mean cold-render `prompt_chars`
- **THEN** the condensation is accepted and the run dir plus scorecard are archived
  under `evals/runs/`

#### Scenario: Sweep regresses quality

- **WHEN** the post-condensation sweep shows a lower first-shot rate or higher
  attempts-to-pass than the preceding run
- **THEN** the condensation is reverted or narrowed and re-measured

---

### Requirement: Cited section names remain resolvable after condensation

Inline renders cite reference sections by name. Any section name referenced from
`prompts/*.md`, `skill/*.md`, or `SKILL.md` SHALL still exist in the condensed
documents, or the referencing text SHALL be updated in the same change.

#### Scenario: A renamed or removed section is still cited

- **WHEN** condensation removes or renames a section named elsewhere in the skill
- **THEN** the citing text is updated in the same change so no citation points at a
  missing section
