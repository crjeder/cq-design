## MODIFIED Requirements

### Requirement: Z-buffered rasterization
The preview renderer SHALL rasterize tessellated geometry with a per-pixel depth test using a pure numpy/Pillow rasterizer, replacing matplotlib mplot3d triangle sorting. It SHALL NOT require OpenGL, EGL, osmesa, a display server, or any new dependency.

#### Scenario: Flat face is shaded uniformly
- **WHEN** a box is rendered from above
- **THEN** every pixel in the interior of the top face has the same color (no per-triangle shading patches)

#### Scenario: Nearer geometry occludes farther geometry
- **WHEN** a smaller box protrudes toward the camera from a larger box
- **THEN** the rendered silhouette and pixels reflect the nearer geometry regardless of triangle order
