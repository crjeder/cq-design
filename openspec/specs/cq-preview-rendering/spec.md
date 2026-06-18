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
The skill SHALL provide `src/render_preview.py` as a CLI that accepts `--script <path>`, `--output <path>`, `--views iso|multi`, and `--cross-sections`, executes the model script to obtain the `result` CadQuery object, and writes the rendered PNG to `--output`. When `--cross-sections` is passed with `--views multi`, the output is a 3x3 nine-view tile.

#### Scenario: Render preview via subprocess
- **WHEN** `python src/render_preview.py --script model.py --output preview.png --views multi` is run
- **THEN** the script executes without error and `preview.png` is created as a valid PNG file

#### Scenario: Missing result variable is an error
- **WHEN** the model script exits without assigning a `result` variable
- **THEN** `render_preview.py` exits with a non-zero code and prints a diagnostic message

#### Scenario: Cross-section flag produces nine-view tile
- **WHEN** `python src/render_preview.py --script model.py --output preview.png --cross-sections` is run
- **THEN** the script executes without error and `preview.png` is a 3x3 nine-view tile

### Requirement: preview.py public API accepts CadQuery objects
`preview.render_single` and `preview.render_multi_view` SHALL accept a CadQuery `Workplane` or `Shape` as their first argument. They SHALL NOT accept `trimesh.Trimesh` objects. `render_multi_view` SHALL additionally accept an optional `cross_sections` boolean parameter (default `False`).

#### Scenario: render_multi_view produces six-view PNG by default
- **WHEN** `preview.render_multi_view(workplane, output_path)` is called with a valid CadQuery workplane and no `cross_sections` argument
- **THEN** a PNG is written to `output_path` containing six views: isometric, front, right, back-isometric, top, bottom

#### Scenario: render_multi_view with cross_sections produces nine-view PNG
- **WHEN** `preview.render_multi_view(workplane, output_path, cross_sections=True)` is called
- **THEN** a PNG is written to `output_path` containing nine views: six exterior views plus Section Y, Section X, Section Z

#### Scenario: pyrender is not imported
- **WHEN** `import preview` is executed
- **THEN** no import of `pyrender` or `OpenGL` occurs
