## ADDED Requirements

### Requirement: Cross-section views are appended to the multi-view tile
When cross-section rendering is enabled, `preview.render_multi_view` SHALL produce a 3x3 PNG tile where the first two rows contain the six standard exterior views and the third row contains three cross-section views: Section Y (XZ plane cut at Y centroid), Section X (YZ plane cut at X centroid), and Section Z (XY plane cut at Z centroid).

#### Scenario: Cross-section tile has nine views
- **WHEN** `preview.render_multi_view(workplane, output_path, cross_sections=True)` is called
- **THEN** the output PNG is a 3x3 tile with six exterior views in rows 1-2 and three cross-section views in row 3

#### Scenario: Default tile is unchanged
- **WHEN** `preview.render_multi_view(workplane, output_path)` is called without the `cross_sections` argument
- **THEN** the output PNG is the standard 3x2 tile with six exterior views and no cross-section views

### Requirement: Cross-section views use Boolean half-space cut
Each cross-section view SHALL be produced by cutting the model with an axis-aligned half-space box whose face lies at the model's centroid along that axis, keeping the negative half. The cut solid SHALL be tessellated and rendered using the same OCC + matplotlib pipeline as exterior views.

#### Scenario: Section Y view reveals internal geometry at Y centroid
- **WHEN** a hollow box model is rendered with `cross_sections=True`
- **THEN** the Section Y view shows the interior cavity visible from the front direction

#### Scenario: Boolean cut failure degrades gracefully
- **WHEN** a cross-section Boolean cut raises an OCC exception
- **THEN** the affected cross-section view is replaced with a blank tile and a warning is written to stderr; the remaining views are rendered normally

### Requirement: render_preview.py exposes --cross-sections flag
The `render_preview.py` CLI SHALL accept an optional `--cross-sections` flag that, when present, passes `cross_sections=True` to `render_multi_view`. It SHALL have no effect when `--views iso` is used.

#### Scenario: --cross-sections flag produces nine-view PNG
- **WHEN** `python src/render_preview.py --script model.py --output preview.png --cross-sections` is run
- **THEN** the script exits 0 and `preview.png` contains a 3x3 view tile

#### Scenario: --cross-sections ignored for iso view
- **WHEN** `python src/render_preview.py --script model.py --output preview.png --views iso --cross-sections` is run
- **THEN** the script exits 0 and produces a single isometric view (flag silently ignored)

### Requirement: run_cadquery_model.py forwards --cross-sections
`run_cadquery_model.py` SHALL accept a `--cross-sections` flag and, when present, forward it to the `render_preview.py` subprocess call. The flag SHALL only be forwarded when `--preview` is also set.

#### Scenario: Wrapper forwards flag to renderer
- **WHEN** `run_cadquery_model.py model.py --preview --cross-sections` is invoked
- **THEN** `render_preview.py` receives `--cross-sections` in its argv and the JSON output's `previews` contains a path to a nine-view PNG

#### Scenario: --cross-sections without --preview is a no-op
- **WHEN** `run_cadquery_model.py model.py --cross-sections` is invoked without `--preview`
- **THEN** no preview is rendered and the flag is ignored
