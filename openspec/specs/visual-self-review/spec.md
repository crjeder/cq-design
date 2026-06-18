# Visual Self-Review

## Purpose

Defines requirements for a visual self-review step in the Phase 3 part loop, where Claude inspects each rendered preview against design intent (via a structured checklist) before a part is marked done, records `visual_mismatch` findings, and surfaces review outcomes to the user.

## Requirements

### Requirement: Part loop performs a visual self-review before a part is marked done

During the Phase 3 part loop, after a part passes geometry validation and a preview PNG is produced, Claude SHALL visually inspect the rendered preview against the design intent before marking the part done. A part SHALL only be considered done when geometry validation passes AND the visual self-review confirms the render matches intent.

#### Scenario: Geometry passes and render matches intent
- **WHEN** `run_cadquery_model.py` returns `success: true` with no blocking errors and a preview PNG, and the visual self-review finds no mismatch
- **THEN** the part is marked done, its `geometry.bbox` is recorded, and the loop advances to the next part

#### Scenario: Geometry passes but render does not match intent
- **WHEN** geometry validation passes but the visual self-review finds the render does not match the design intent (wrong shape, missing or misplaced feature, mirrored cutout, wrong proportions)
- **THEN** the part is NOT marked done, a `visual_mismatch` finding describing the discrepancy is recorded, and (if the attempt budget is not exhausted) the loop retries with a targeted fix driven by that description

#### Scenario: Geometry fails
- **WHEN** geometry validation returns a blocking error
- **THEN** the geometry error is handled first and the visual self-review is skipped for that attempt

### Requirement: Visual review uses a structured checklist injected as a reference

The skill SHALL provide a reusable visual-review checklist as an injected reference, and the part loop SHALL evaluate each rendered part against every checklist item. The checklist SHALL cover at minimum: overall shape matches the request, all planned features and interfaces are present, proportions are reasonable, no floating or disconnected bodies, a flat bed face exists at Z = 0, and the print orientation matches the plan.

#### Scenario: Checklist is available to the part loop
- **WHEN** the Phase 3 part loop runs
- **THEN** the visual-review checklist reference is loaded into context and each rendered part is evaluated against every checklist item

#### Scenario: A single failed checklist item is a mismatch
- **WHEN** the render fails one or more checklist items
- **THEN** the review result is a `visual_mismatch` naming the failed item(s), not a pass

### Requirement: visual_mismatch is a documented loop finding

The `visual_mismatch` finding SHALL be documented in the SKILL error-handling reference with its meaning and corrective action. It SHALL be recorded by Claude within the part loop and SHALL participate in the same retry budget as geometry errors. It SHALL NOT be emitted by `run_cadquery_model.py` (the wrapper JSON contract is unchanged).

#### Scenario: visual_mismatch documented in error reference
- **WHEN** a reader consults the SKILL error-handling reference table
- **THEN** `visual_mismatch` appears with its meaning and the corrective action (re-examine intent, fix the responsible parameter or geometry)

#### Scenario: Wrapper contract unchanged
- **WHEN** `run_cadquery_model.py` runs a model
- **THEN** its JSON output keys and error types are unchanged and contain no `visual_mismatch` entry

### Requirement: Visual review outcome is surfaced to the user

When a part is marked done, Claude SHALL display the reviewed preview PNG. When the attempt budget is exhausted with an unresolved `visual_mismatch`, Claude SHALL summarize the remaining mismatch to the user and ask conversationally how to proceed (provide a hint, accept as-is, or skip the part).

#### Scenario: Done part shows its preview
- **WHEN** a part is marked done
- **THEN** the reviewed preview PNG is displayed to the user

#### Scenario: Unresolved mismatch after retries
- **WHEN** the attempt budget is exhausted and a `visual_mismatch` remains
- **THEN** Claude summarizes the mismatch and asks the user how to proceed
