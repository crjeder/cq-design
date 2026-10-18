## ADDED Requirements

### Requirement: Audit prompt names preview panels with the renderer's camera labels
The audit prompt (`prompts/audit.md`) SHALL describe the 2x2 preview tile using the same panel titles and camera directions `src/preview.py` renders: "Viewed from South (looking North)" top-left, "Viewed from West (looking East)" top-right, "Viewed from above (looking down)" bottom-left, and isometric bottom-right. It SHALL NOT describe the front panel as looking along -Y.

#### Scenario: Front panel direction matches the render
- **WHEN** `prompts/audit.md` is rendered
- **THEN** its panel description names the top-left panel "Viewed from South (looking North)" and contains no "looking -Y"

#### Scenario: Mirroring check uses the correct handedness
- **WHEN** the auditor checks an `interfaces[]` entry on the East wall in the top-left panel
- **THEN** the prompt's camera description places East on the viewer's right, matching the rendered image
