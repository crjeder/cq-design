# Spec delta: cq-preview-rendering

## MODIFIED Requirements

### Requirement: preview.py public API accepts CadQuery objects

`preview.render_single` and `preview.render_multi_view` SHALL accept a CadQuery
`Workplane` or `Shape` as their first argument. They SHALL NOT accept
`trimesh.Trimesh` objects.

`render_multi_view` SHALL, by default, produce a 2x2 first-angle (DIN) projection
tile with these four panels:

- **Front-position panel** (camera looking along -Y) in the top-left
- **Side-position panel** (the view-from-left, camera on the -X side looking
  toward +X) in the top-right -- first-angle places the left-side view on the right
- **Top-position panel** (camera looking along -Z) in the bottom-left -- first-angle
  places the top view below the front
- **Isometric** (pictorial) in the bottom-right

The three orthographic panels SHALL use true orthographic projection
(`ax.set_proj_type("ortho")`) with exact axis-aligned camera angles and no
perspective tilt, so edges are undistorted. The isometric panel remains pictorial.

Each panel SHALL be labeled using the compass convention documented in
`prompts/planning.md` (North=+Y, East=+X, up=+Z), naming the viewing station (e.g.
"Viewed from North", "Viewed from above"); the labels "Front", "Left side", and
left/right/front/back terms SHALL NOT be used. The label for each panel SHALL be
verified against what the panel actually shows (via an asymmetric fixture whose
compass faces are distinguishable), not derived from prose, so the label, the camera,
and the planning prompt's axis table agree. The camera angles themselves are
unchanged from the previous first-angle layout.

The tile caption SHALL show the overall bounding box (W x D x H mm), volume, triangle
count, and PLA weight estimate; no dimension lines SHALL be drawn on the panels.

#### Scenario: render_multi_view produces a 2x2 first-angle tile by default

- **WHEN** `preview.render_multi_view(workplane, output_path)` is called with a valid
  CadQuery workplane and no `cross_sections` argument
- **THEN** a PNG is written containing four labeled panels in first-angle placement,
  the three orthographic ones labeled with compass-convention view names and the
  fourth labeled Isometric

#### Scenario: Panel labels match the compass convention

- **WHEN** the multi-view tile is rendered for a fixture with a marker on its North
  (+Y) face
- **THEN** the panel whose label names the North viewing station is the one showing
  the marker, and no panel label contains "Front", "Left", "left", or "right"

#### Scenario: Orthographic panels are undistorted

- **WHEN** any orthographic panel is rendered
- **THEN** it is drawn with orthographic projection and an exact axis-aligned camera
  (parallel edges stay parallel; no perspective convergence or tilt)

#### Scenario: Overall dimensions appear only in the caption

- **WHEN** the tile is rendered
- **THEN** the overall bounding box W x D x H appears in the caption and no dimension
  lines are drawn over the panels

#### Scenario: pyrender is not imported

- **WHEN** `import preview` is executed
- **THEN** no import of `pyrender` or `OpenGL` occurs
