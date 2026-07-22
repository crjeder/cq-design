# Profile Stub Review

## Purpose

Defines requirements for a Step 0 profile-stub checkpoint in the Phase 3 part loop: a cheap 2D-profile stub rendered and reviewed before a part is authored in full, so a wrong silhouette is caught before the cost of full authoring is spent. Review frequency for the stub checkpoint follows the plan's `review_policy` (see `planning-phase` spec).

## Requirements

### Requirement: Part loop renders a profile stub before full authoring

Before authoring a part's full construction script, the Phase 3 part loop SHALL
generate a minimal stub script consisting of the part's characteristic 2D profile
extruded to a nominal thickness, and render it via `run_cadquery_model.py
--preview`. This SHALL occur as Step 0 of the part loop, before the archetype-match
and full-authoring steps.

#### Scenario: Stub generated before full script

- **WHEN** a part begins its part-loop pass
- **THEN** a profile-only stub script is authored and rendered before any
  full-featured construction script is written for that part

#### Scenario: Stub reuses the existing preview path

- **WHEN** the stub is rendered
- **THEN** it is rendered through the same `run_cadquery_model.py --preview`
  mechanism used elsewhere in the part loop, with no new renderer introduced

### Requirement: Stub checkpoint frequency follows the plan's review policy

When the plan's effective `review_policy` (see `planning-phase` spec) is
`checkpoints` or `every_stage`, the rendered stub SHALL be displayed to the user
for silhouette confirmation, and the loop SHALL pause until the user approves,
requests a change, or skips. When the effective `review_policy` is `minimal`, the
stub SHALL still be generated and rendered, but SHALL be evaluated by Claude
against design intent without pausing for the user (self-review), matching how
autonomous parts already self-review geometry today.

#### Scenario: Stub checkpoint shown under checkpoints or every_stage

- **WHEN** the plan's effective `review_policy` is `checkpoints` or `every_stage`
- **THEN** the rendered stub is shown to the user and the loop waits for approval,
  a requested change, or a skip before proceeding to full authoring

#### Scenario: Stub self-reviewed under minimal

- **WHEN** the plan's effective `review_policy` is `minimal`
- **THEN** the stub is still rendered, evaluated by Claude against the part's
  design intent, and the loop proceeds to full authoring without a user pause

#### Scenario: User requests a change at the stub checkpoint

- **WHEN** the user requests a change to the stub's silhouette
- **THEN** the stub is re-authored applying the feedback, re-rendered, and the
  checkpoint is presented again before full authoring begins

### Requirement: Stub is disposable and not reused as the base-shape stage

The profile stub SHALL be treated as scoped to silhouette confirmation only. It
SHALL NOT be reused as progressive build's base-shape stage output, and its
geometry SHALL NOT be required to match the construction plan later used for the
part's base-shape stage.

#### Scenario: Stub discarded after checkpoint

- **WHEN** a part's stub checkpoint is approved
- **THEN** full authoring (including progressive build's own base-shape stage, if
  applicable) proceeds independently of the stub's script or geometry
