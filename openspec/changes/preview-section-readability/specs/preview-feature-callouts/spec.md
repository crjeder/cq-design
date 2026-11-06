## ADDED Requirements

### Requirement: Callouts are placed only where the feature is visible
Each callout SHALL be drawn on the first panel (orthographic panels in tile order, then isometric) where a z-buffer test shows its projected anchor is not occluded.

#### Scenario: Interior feature occluded in top view
- **WHEN** a callout anchor is occluded in the top panel but visible in the isometric panel
- **THEN** its badge is drawn on the isometric panel only

### Requirement: Hidden callouts are marked in the legend
A callout visible in no panel SHALL get no badge and SHALL appear in the legend as `NAME (hidden)`.

#### Scenario: Fully enclosed feature
- **WHEN** a callout anchor is occluded in every panel
- **THEN** the legend lists it as hidden and no badge is drawn

### Requirement: Coincident badges merge
Callouts whose chosen-panel positions fall within 12 px SHALL be merged into one badge, with the legend entry `NAME xN` naming the group.

#### Scenario: Four rim rails project to one point
- **WHEN** four callouts project within 12 px of each other in the top panel
- **THEN** one badge is drawn and the legend shows a single `rim_rails x4` entry
