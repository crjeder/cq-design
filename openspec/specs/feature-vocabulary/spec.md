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

### Requirement: Partial revolutions are described by clock position on a paired view, not by direction words

When user-facing prose describes a partial revolution (a hinge sweep, a dial or screw-pattern
angular position, or any rotation about a single axis), the skill SHALL express the target
position as a clock reading (e.g. "the 90° position", "12 o'clock", "3 o'clock") read off one
of the compass viewing stations defined in the `cq-preview-rendering` spec (South, West,
above), choosing the station whose sight-line is the rotation axis: Z pairs with "above", Y
pairs with "South", X pairs with "West". The skill's own prose SHALL NOT use the words
"clockwise" or "counterclockwise" to describe rotation direction, because right-hand-rule-
positive rotation reads clockwise on the South/West stations and counterclockwise on the
above station, and a single direction word has no axis-independent correct sign. This
convention SHALL NOT introduce a `BUILD_PLAN.json` field; it governs prose only, and does not
change the right-hand-rule sign convention already used by `placement.rotate` or the
joint-contract `dof.direction`.

When the rotation axis is not aligned with X, Y, or Z (no paired viewing station has that
axis as its sight-line), the skill SHALL instead describe the rotation by naming its start and
end reference features (e.g. "from flush with `object a` to flush with `object b`") rather
than a clock position.

#### Scenario: Hinge sweep described by clock position on the paired view

- **WHEN** the skill describes a lid hinged about the Z axis swinging open at a checkpoint
- **THEN** the prose names the "above" view and a clock position (e.g. "swings to the 90°
  position in the above view"), not "clockwise" or "counterclockwise"

#### Scenario: Direction words are never used for rotation

- **WHEN** the skill produces any checkpoint prose describing a partial revolution about X, Y,
  or Z
- **THEN** the prose contains no instance of "clockwise" or "counterclockwise"

#### Scenario: View is paired to the rotation axis

- **WHEN** the skill states a clock position for a rotation about the Y axis
- **THEN** the prose names the "South" view, not "West" or "above"

#### Scenario: Retired view names are not reused for rotation prose

- **WHEN** the skill describes a rotation in any view
- **THEN** the view is named using the compass station terms (South/West/above), never
  "front view", "side view", or "top view"

#### Scenario: Oblique axis falls back to named features

- **WHEN** a rotation's axis does not align with X, Y, or Z
- **THEN** the skill describes the rotation by its start and end reference features instead of
  a clock position
