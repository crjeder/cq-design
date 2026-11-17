## MODIFIED Requirements

### Requirement: Ambiguous feature references are echoed back before acting

When the user refers to a feature by a spatial description or an unagreed word, the
skill SHALL restate the reference using the agreed feature name (the stage label shown
on the labeled preview, or the plan name when it matches) before applying a change based
on it. When the mapping is not obvious, the skill SHALL ask for confirmation instead of
guessing.

#### Scenario: Spatial reference resolved to a name

- **WHEN** the user says "make the slot on the West side wider" and the part declares
  exactly one slot-like interface on the West face
- **THEN** the skill restates it as the agreed name (e.g. "widening `cable_slot`") in
  the same turn it applies the change

#### Scenario: Ambiguous reference is confirmed, not guessed

- **WHEN** the user's spatial description plausibly matches more than one declared
  feature
- **THEN** the skill asks which named feature is meant before re-authoring the part
