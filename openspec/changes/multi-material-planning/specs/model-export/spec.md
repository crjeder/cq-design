## ADDED Requirements

### Requirement: Multi-material 3MF
A 3MF export of a plan with more than one resolved material SHALL record each body's color
and filament slot so Bambu Studio / OrcaSlicer open it with filaments pre-assigned. A plan
with a single material SHALL export as before.

#### Scenario: Two-material export
- **WHEN** two unions resolve to different slots
- **THEN** the 3MF carries two distinct color entries and two distinct extruder assignments

#### Scenario: STL and STEP unchanged
- **WHEN** the same plan is exported as STL or STEP
- **THEN** output is identical to a single-material plan
