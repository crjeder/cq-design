# Skill Doc Structure (delta)

## MODIFIED Requirements

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
