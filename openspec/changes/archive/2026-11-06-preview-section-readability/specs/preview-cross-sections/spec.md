## ADDED Requirements

### Requirement: Section caps are visually distinct
Section renders SHALL draw the cut cap (triangles lying on the cut plane) in a colour distinct from all other faces, with an outline, so the cut profile is distinguishable from surfaces sharing its normal.

#### Scenario: Cap versus coplanar-normal surface
- **WHEN** a z-cut passes through a plate whose top face also has a +z normal
- **THEN** the cap pixels and the plate-top pixels have different colours

### Requirement: Renders draw depth-discontinuity edges
Orthographic tile panels, section renders and detail renders SHALL draw edge lines at silhouette and depth discontinuities derived from the z-buffer.

#### Scenario: Channel floor and rim separate
- **WHEN** a part has a channel floor at a different depth from its rim
- **THEN** an edge line is drawn between them in the rendered panel

### Requirement: Blank sections are flagged
Section rendering SHALL report `informative: false` when the cap silhouette equals the uncut silhouette and the cap has no inner hole, and `informative: true` otherwise. `render_preview.py` SHALL print the flag next to the section path.

#### Scenario: Solid block cut through a solid region
- **WHEN** a section cuts a solid block with no hole or notch
- **THEN** the result reports `informative: false`

#### Scenario: Cut through a bore
- **WHEN** a section passes through a bore axis
- **THEN** the result reports `informative: true`

### Requirement: Builder keeps the rendered validate command
The builder prompt SHALL instruct the builder to run the rendered validate command verbatim, adding cuts but never replacing the supplied `--extra-section` cuts.

#### Scenario: Builder adds a cut
- **WHEN** the builder wants an extra cut
- **THEN** it appends `--extra-section` flags to the supplied command rather than substituting its own
