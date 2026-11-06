## ADDED Requirements

### Requirement: Feature frame is derived from the solid
For an interface with `position_mm`, the system SHALL derive the feature bounding box, dominant face normal (snapped to a world axis) and depth from the built solid near that position, excluding host-wall faces, without requiring any schema field. When no faces are found the feature SHALL be reported as not located.

#### Scenario: Hole in a wall
- **WHEN** an interface positioned on a 3 mm wall has a 5 mm bore
- **THEN** the frame bbox covers the bore, the normal is the wall normal, and depth is 3 mm

#### Scenario: No geometry near the position
- **WHEN** no solid faces lie within the search window
- **THEN** the feature is listed as not located and no view is rendered for it

### Requirement: Feature views show and mark the feature
Each feature view SHALL use a camera along the feature normal framed on the feature bbox, SHALL draw the feature's marker at its projected position, and SHALL fall back to the isometric camera when the anchor is occluded.

#### Scenario: Feature on the bottom face
- **WHEN** a feature sits on the bottom face
- **THEN** the view looks at the bottom face and the marker is drawn on the feature

### Requirement: Features with depth get a section through their axis
A feature whose depth is at least 0.5 mm SHALL get a section whose plane contains the feature normal and passes through the bbox centre. A flat feature SHALL get no section.

#### Scenario: Blind hole
- **WHEN** a feature has 4 mm depth
- **THEN** a section through its axis shows the hole depth, with the marker

#### Scenario: Flat engraving
- **WHEN** a feature has depth below 0.5 mm
- **THEN** no section is rendered for it

### Requirement: Preview sheet is a relevance-ranked 2 x 2 grid capped at four tiles
The system SHALL compose at most four tiles into one 2 x 2 preview sheet. Tiles SHALL be ranked: features named in the current user prompt first, then features targeted by `correction` or `clarification` request_log entries (including ask_user answers), then other request_log mentions, then remaining features by size; whole-part sections fill any remaining tiles. Each tile SHALL also be written as a full-size file. Features not shown SHALL be listed as "(not shown)".

#### Scenario: Six positioned features, one named by the user
- **WHEN** the user's prompt names `usb_port` among six positioned interfaces
- **THEN** `usb_port` is a tile and the sheet has exactly four tiles, the other two features not shown listed as "(not shown)"

#### Scenario: No features qualify
- **WHEN** a part has no positioned interfaces
- **THEN** the sheet contains only whole-part section tiles

#### Scenario: User-changed feature outranks size
- **WHEN** a small feature was changed by a `correction` entry and a larger feature was not
- **THEN** the small feature is selected before the larger one
