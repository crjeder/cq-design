## MODIFIED Requirements

### Requirement: Preview rendering uses CadQuery tessellation without OpenGL
The preview renderer SHALL generate PNG images from a CadQuery `Workplane` or `Shape` object using the OCC tessellation API and a numpy z-buffer rasterizer. It SHALL NOT require OpenGL, EGL, osmesa, or any display server.

#### Scenario: Headless preview succeeds without display
- **WHEN** `run_cadquery_model.py model.py --preview` is invoked in an environment with no display server and no GPU
- **THEN** a multi-view preview PNG is produced and its path appears in `previews[]` in the JSON output

#### Scenario: Preview renders from live CQ geometry
- **WHEN** the preview renderer is invoked for a model
- **THEN** it re-runs the model script in the CadQuery environment and tessellates the `result` workplane directly, without loading the STL file

## ADDED Requirements

### Requirement: Z-buffered rasterization
The preview renderer SHALL rasterize tessellated geometry with a per-pixel depth test using a pure numpy/Pillow rasterizer, replacing matplotlib mplot3d triangle sorting. It SHALL NOT require OpenGL, EGL, osmesa, a display server, or any new dependency.

#### Scenario: Flat face is shaded uniformly
- **WHEN** a box is rendered from above
- **THEN** every pixel in the interior of the top face has the same color (no per-triangle shading patches)

#### Scenario: Nearer geometry occludes farther geometry
- **WHEN** a smaller box protrudes toward the camera from a larger box
- **THEN** the rendered silhouette and pixels reflect the nearer geometry regardless of triangle order

#### Scenario: Callouts follow the projection
- **WHEN** callouts are supplied to a multi-view render
- **THEN** badges appear on the three orthographic panels at the feature's projected position and not on the isometric panel
