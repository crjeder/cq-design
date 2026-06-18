# Progressive Build

## Purpose

Defines requirements for a progressive (staged, user-checkpointed) build mode in the Phase 3 part loop, where complex parts are constructed stage by stage with user checkpoints between each, gated by a stated complexity heuristic and overridable by the user, while converging on the same completion bar as the autonomous build.

## Requirements

### Requirement: A complexity gate selects progressive or autonomous build per part

The Phase 3 part loop SHALL decide per part whether to build progressively (staged, with user checkpoints) or autonomously (the existing single-shot loop). By default the decision SHALL be driven by a stated complexity gate: a part SHALL build progressively when it has at least one `interfaces` entry OR its `blocks_needed` count meets or exceeds a stated threshold; otherwise it SHALL build autonomously. The gate condition and threshold SHALL be stated in `SKILL.md` as tunable values.

#### Scenario: Simple part builds autonomously
- **WHEN** a part has no `interfaces` and a `blocks_needed` count below the threshold
- **THEN** the part is built with the existing autonomous part loop and no progressive checkpoints are shown

#### Scenario: Complex part builds progressively
- **WHEN** a part has at least one `interfaces` entry or a `blocks_needed` count at or above the threshold
- **THEN** the part is built progressively with user checkpoints between stages

#### Scenario: Gate values are stated in SKILL.md
- **WHEN** a reader consults the Phase 3 part loop documentation
- **THEN** the complexity gate condition and the threshold are stated explicitly as tunable values

### Requirement: Progressive build proceeds in stages with a checkpoint between each

Progressive build SHALL construct a part in the ordered stages base shape, then features, then finishing. At each stage the loop SHALL write the current `build/<part_id>.py`, validate and render it, run the visual self-review scoped to the features expected at that stage, and then pause at a checkpoint before proceeding. The user SHALL always review a geometrically valid stage: geometry errors at a stage SHALL be fixed before its checkpoint is shown.

#### Scenario: Stage order
- **WHEN** a part is built progressively
- **THEN** stages are produced in the order base shape, features, finishing

#### Scenario: Stage is validated before its checkpoint
- **WHEN** a stage is authored
- **THEN** it is run through `run_cadquery_model.py --preview` and any geometry errors are fixed before the checkpoint is presented to the user

#### Scenario: Visual self-review runs per stage
- **WHEN** a stage passes geometry validation
- **THEN** the visual self-review checklist is applied to that stage scoped to the features expected so far, before the checkpoint

### Requirement: Each checkpoint presents the stage and offers approve, request-change, or skip-remaining

At each checkpoint Claude SHALL display the staged preview PNG and a one-line summary of what the stage added, then wait for the user. The user SHALL be able to approve (advance to the next stage), request a change (re-author the current stage with the feedback, then re-present the checkpoint), or skip remaining checkpoints (finish the part with the autonomous loop).

#### Scenario: Approve advances
- **WHEN** the user approves a checkpoint
- **THEN** the loop advances to the next stage, or completes the part if finishing was the last stage

#### Scenario: Request change re-authors the stage
- **WHEN** the user requests a change at a checkpoint
- **THEN** the current stage is re-authored applying the feedback, re-validated and re-reviewed, and the checkpoint is presented again

#### Scenario: Skip remaining finishes autonomously
- **WHEN** the user chooses to skip remaining checkpoints
- **THEN** the rest of the part is completed with the autonomous loop and no further checkpoints are shown for that part

### Requirement: Build mode is user-overridable regardless of the gate

The user SHALL be able to force progressive build or force autonomous build for a part or a run, overriding the complexity gate. Absent an override, the gate decision SHALL apply.

#### Scenario: User forces autonomous on a complex part
- **WHEN** the user opts out of progressive build and a part would otherwise be gated to progressive
- **THEN** the part is built autonomously with no checkpoints

#### Scenario: User forces progressive on a simple part
- **WHEN** the user opts in to progressive build and a part would otherwise be gated to autonomous
- **THEN** the part is built progressively with checkpoints

#### Scenario: No override uses the gate
- **WHEN** the user gives no mode override
- **THEN** the complexity gate decides the mode

### Requirement: Progressive and autonomous paths converge on the same completion bar

Regardless of build mode, a completed part SHALL satisfy the same plan dimensions and pass the full visual self-review at completion. Progressive build SHALL NOT lower the completion criteria.

#### Scenario: Progressive part meets the autonomous completion bar
- **WHEN** a part finishes via progressive build
- **THEN** its final geometry satisfies the plan dimensions within tolerance and passes the full visual self-review, the same as an autonomously built part
