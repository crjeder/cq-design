## ADDED Requirements

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
