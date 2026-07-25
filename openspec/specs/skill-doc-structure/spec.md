# Skill Doc Structure

## Purpose

Defines how the `cq-design` skill's documentation is split across a small
always-loaded SKILL.md, per-phase detail files, and block-gated reference
data, so that the trigger-time load cost stays small while phase- and
block-specific detail remains fully available when actually needed.

## Requirements

### Requirement: Core SKILL.md stays under 10 KB
SKILL.md SHALL contain only always-needed content - trigger, overview, phase
overview with per-phase summaries and read pointers, prerequisites pointer,
slash-command entry points, JSON contract, typed-error reference, DFM constraint
values, coordinate system, generated script rules, and the key-files quick
reference - and SHALL be under 10 KB.

#### Scenario: Trigger load cost
- **WHEN** the skill triggers for any invocation (`/render`, `/deliver`, `/plan`,
  or a full design request)
- **THEN** the initially loaded SKILL.md is under 10 KB and contains no phase-local
  step-by-step procedures

---

### Requirement: Phase detail lives in per-phase files
The skill SHALL provide `skill/phase0_sourcing.md`, `skill/phase1_requirements.md`,
`skill/phase2_planning.md`, `skill/phase3_build.md`, and `skill/phase4_deliver.md`,
carrying the full moved content of their SKILL.md phase sections without loss.
`skill/phase0_sourcing.md` carries the sourcing-triage decision ladder and its
per-rung handling, referencing (not duplicating) the Phase 1 search workflow.

#### Scenario: Content preservation
- **WHEN** the split lands
- **THEN** every instruction removed from SKILL.md's phase sections appears
  verbatim in exactly one `skill/phase*.md` file

#### Scenario: Build-phase detail location
- **WHEN** the part loop, progressive build, orientation loop, or kinematic
  validation walkthrough is needed
- **THEN** it is found in `skill/phase3_build.md`

#### Scenario: Sourcing-triage detail location
- **WHEN** Phase 0 sourcing triage is entered
- **THEN** the decision ladder, license rules, and per-rung handling are found in
  `skill/phase0_sourcing.md`, and SKILL.md's phase overview lists Phase 0 with a
  mandatory read pointer to it

---

### Requirement: Mandatory read at phase entry
Each phase section in core SKILL.md SHALL consist of a short summary plus an
instruction that the corresponding `skill/phase*.md` file MUST be read in full
before executing that phase. Phase summaries SHALL NOT contain step numbers or
commands sufficient to run the phase without the file.

#### Scenario: Entering the build phase
- **WHEN** the pipeline transitions into Phase 3
- **THEN** SKILL.md directs reading `skill/phase3_build.md` in full before any part
  is authored

#### Scenario: Command-scoped invocation skips unrelated phases
- **WHEN** the user invokes `/render`
- **THEN** only the phase files relevant to rendering are read, and Phase 1-3
  procedure files are not loaded

---

### Requirement: Hardware dimension tables are block-gated reference data
Hardware dimension tables SHALL move from SKILL.md to `reference/hardware_dims.md`
and SHALL be read only when a fastener or hardware block appears in the plan's
`blocks_needed`.

#### Scenario: Plan with fastener blocks
- **WHEN** a part's `blocks_needed` includes a fastener/hardware block
- **THEN** `reference/hardware_dims.md` is read before authoring that part

#### Scenario: Plan without hardware
- **WHEN** no part uses a fastener/hardware block
- **THEN** `reference/hardware_dims.md` is never loaded in the session

---

### Requirement: Phase file paths resolve via SKILL_DIR
All `skill/*.md` and `reference/hardware_dims.md` reads SHALL use SKILL_DIR-relative
paths, consistent with the skill-invocation-path-resolution capability.

#### Scenario: Skill invoked from a foreign working directory
- **WHEN** the shell cwd is outside the skill root
- **THEN** phase files are still found via `$SKILL_DIR/skill/<file>.md`
