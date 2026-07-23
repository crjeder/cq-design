# Spec: feature-vocabulary

## Purpose

Defines the shared vocabulary the skill uses when talking about spatial directions and
part features with the user: the compass convention for spatial prose, and the rule
for resolving ambiguous feature references to agreed plan names before acting.

## Requirements

### Requirement: User-facing spatial prose uses the compass convention

All user-facing prose produced by the skill (checkpoint messages, plan summaries,
review questions, fix confirmations) SHALL express directions and locations using the
documented compass convention (North/South/East/West, up/down) as defined in
`prompts/planning.md`. The terms left/right/front/back SHALL appear in user-facing
prose only when quoting or restating the user's own words. The phase documents
(`skill/phase2_planning.md`, `skill/phase3_build.md`) SHALL state this rule where
checkpoint prose is specified.

#### Scenario: Checkpoint prose uses compass terms

- **WHEN** the skill describes a feature's location at a review checkpoint
- **THEN** the location is given in compass/up-down terms (e.g. "on the East face"),
  not left/right/front/back

#### Scenario: Quoting the user is exempt

- **WHEN** the user writes "the hole on the left" and the skill restates it
- **THEN** the quoted phrase may keep "left", but the skill's own restatement maps it
  to a compass term or an agreed feature name

### Requirement: Ambiguous feature references are echoed back before acting

When the user refers to a feature by a spatial description or an unagreed word, the
skill SHALL restate the reference using the agreed plan name (and badge number when a
callout preview exists) before applying a change based on it. When the mapping is not
obvious, the skill SHALL ask for confirmation instead of guessing.

#### Scenario: Spatial reference resolved to a name

- **WHEN** the user says "make the slot on the West side wider" and the part declares
  exactly one slot-like interface on the West face
- **THEN** the skill restates it as the agreed name (e.g. "widening `cable_slot` (2)")
  in the same turn it applies the change

#### Scenario: Ambiguous reference is confirmed, not guessed

- **WHEN** the user's spatial description plausibly matches more than one declared
  feature
- **THEN** the skill asks which named feature is meant before re-authoring the part
