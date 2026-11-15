## ADDED Requirements

### Requirement: Whole-part sections are chosen by slice analysis
The system SHALL sample slices along each axis and score them by inner-loop count, void area fraction and area change relative to neighbouring slices, and SHALL select the best at most two cuts overall, excluding any within 0.5 mm of a feature or reserved cut. Bore/boss cuts from `section_select` SHALL remain and take precedence when they show more features.

#### Scenario: U-profile shelf
- **WHEN** a part is a U-channel with notches and no bores
- **THEN** a cut across the channel (showing the U profile) is selected

#### Scenario: Enclosure
- **WHEN** a part is a hollow enclosure with internal posts
- **THEN** a mid-height cut showing walls and posts is selected

### Requirement: Interface cuts use the feature frame
For an interface with a derived feature frame, the cut axis and position SHALL come from the frame (plane containing the normal), not from the `wall` name or the largest position component. Interfaces without a frame SHALL keep the existing wall/position fallback.

#### Scenario: Slot on a top wall
- **WHEN** a slot sits on the top wall with its long direction along x
- **THEN** the cut plane contains the z normal and the slot's long axis rather than slicing across z
