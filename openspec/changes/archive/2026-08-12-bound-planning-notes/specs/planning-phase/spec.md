## ADDED Requirements

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

## MODIFIED Requirements

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
