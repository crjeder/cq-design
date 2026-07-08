# Spec: cq-preview-rendering

## Purpose

Defines how the skill renders preview PNG images from CadQuery geometry using OCC tessellation and matplotlib, without any OpenGL or display-server dependency.
## Requirements
### Requirement: Preview rendering uses CadQuery tessellation without OpenGL
The preview renderer SHALL generate PNG images from a CadQuery `Workplane` or `Shape` object using the OCC tessellation API and matplotlib (Agg backend). It SHALL NOT require OpenGL, EGL, osmesa, or any display server.

#### Scenario: Headless preview succeeds without display
- **WHEN** `run_cadquery_model.py model.py --preview` is invoked in an environment with no display server and no GPU
- **THEN** a multi-view preview PNG is produced and its path appears in `previews[]` in the JSON output

#### Scenario: Preview renders from live CQ geometry
- **WHEN** the preview renderer is invoked for a model
- **THEN** it re-runs the model script in the CadQuery environment and tessellates the `result` workplane directly, without loading the STL file

### Requirement: render_preview.py subprocess entry point

The skill SHALL provide `src/render_preview.py` as a CLI that accepts `--script
<path>`, `--output <path>`, `--views iso|multi`, and `--cross-sections`, executes the
model script to obtain the `result` CadQuery object, and writes the rendered PNG to
`--output`. With `--views multi` and no `--cross-sections`, the output is the default
2x2 first-angle tile. When `--cross-sections` is passed, the section views are written
as **separate files** (see the `preview-cross-sections` capability), not appended to
the `--output` tile.

#### Scenario: Render preview via subprocess

- **WHEN** `python src/render_preview.py --script model.py --output preview.png --views
  multi` is run
- **THEN** the script executes without error and `preview.png` is a valid PNG
  containing the 2x2 first-angle tile

#### Scenario: Missing result variable is an error

- **WHEN** the model script exits without assigning a `result` variable
- **THEN** `render_preview.py` exits with a non-zero code and prints a diagnostic message

#### Scenario: Cross-section flag writes separate section files

- **WHEN** `python src/render_preview.py --script model.py --output preview.png
  --cross-sections` is run
- **THEN** the `--output` tile stays the 2x2 first-angle tile and one PNG per section
  is written as a separate file, their paths returned in `previews[1:]`

### Requirement: preview.py public API accepts CadQuery objects

`preview.render_single` and `preview.render_multi_view` SHALL accept a CadQuery
`Workplane` or `Shape` as their first argument. They SHALL NOT accept
`trimesh.Trimesh` objects.

`render_multi_view` SHALL, by default, produce a 2x2 first-angle (DIN) projection
tile with these four panels:

- **Front** (Vorderansicht, camera looking along -Y) in the top-left
- **Left side** (Seitenansicht, the view-from-left, camera on the -X side looking
  toward +X) in the top-right -- first-angle places the left-side view on the right
- **Top** (Draufsicht, camera looking along -Z) in the bottom-left -- first-angle
  places the top view below the front
- **Isometric** (pictorial) in the bottom-right

The three orthographic panels (Front, Left, Top) SHALL use true orthographic
projection (`ax.set_proj_type("ortho")`) with exact axis-aligned camera angles and no
perspective tilt, so edges are undistorted. The isometric panel remains pictorial.
Each panel SHALL be labeled with its view name. The tile caption SHALL show the
overall bounding box (W x D x H mm), volume, triangle count, and PLA weight estimate;
no dimension lines SHALL be drawn on the panels.

#### Scenario: render_multi_view produces a 2x2 first-angle tile by default

- **WHEN** `preview.render_multi_view(workplane, output_path)` is called with a valid
  CadQuery workplane and no `cross_sections` argument
- **THEN** a PNG is written containing four labeled panels -- Front (top-left), Left
  side (top-right), Top (bottom-left), Isometric (bottom-right)

#### Scenario: Orthographic panels are undistorted

- **WHEN** the Front, Left, or Top panel is rendered
- **THEN** it is drawn with orthographic projection and an exact axis-aligned camera
  (parallel edges stay parallel; no perspective convergence or tilt)

#### Scenario: Overall dimensions appear only in the caption

- **WHEN** the tile is rendered
- **THEN** the overall bounding box W x D x H appears in the caption and no dimension
  lines are drawn over the panels

#### Scenario: pyrender is not imported

- **WHEN** `import preview` is executed
- **THEN** no import of `pyrender` or `OpenGL` occurs

