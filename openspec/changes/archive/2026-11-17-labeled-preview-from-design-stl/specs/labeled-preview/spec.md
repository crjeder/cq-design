## ADDED Requirements

### Requirement: Design-pose STL export from the build script
The system SHALL provide `src/export_design_stl.py <build_script> [out.stl]` that runs the project's build script, takes its `result`, and writes `preview/design.stl` by default with tessellation tolerance 0.05 mm and angular tolerance 0.1 rad. The STL SHALL be in the designed pose (the build pose, before print-pose rotation). A `dict[str, Workplane]` result SHALL be exported as one compound. It SHALL also write `preview/design.features.json` listing, per stage label recorded during the build, the operation, delta bbox, delta centroid and delta volume. On success it SHALL print one JSON object with `success`, `stl`, `features` and `errors`, and exit 0; on failure `success` is false, `errors` is non-empty and the exit code is 1.

#### Scenario: Export writes the STL and feature record
- **WHEN** `export_design_stl.py build/holder.py` runs on a script whose stages are labeled `base_shape` and `hinge_web`
- **THEN** `preview/design.stl` exists and `preview/design.features.json` lists both labels with bbox, centroid and operation

#### Scenario: Script without a result
- **WHEN** the build script finishes without assigning `result`
- **THEN** the exporter exits 1 with `success: false` and an error naming the missing variable

#### Scenario: Stage recorder is off outside the export
- **WHEN** a build script runs through `run_cadquery_model.py` without the export
- **THEN** `cq_verify` records nothing and its return values and errors are unchanged

### Requirement: Labeled preview shows feature names on five views
The system SHALL provide `src/render_labeled.py <stl> <features.json> [out.png]` that writes `preview/<script_stem>_preview_labeled.png` by default. The image SHALL contain five panels in this order: viewed from South, viewed from above, viewed from below (inner faces, Y flipped), isometric, viewed from West, each rendered orthographically with the numpy z-buffer rasterizer. Each feature SHALL be drawn as its name in a coloured box with a leader line to an anchor dot on the part, using one colour per feature. A footer SHALL state the bounding box (W x D x H mm), triangle count and the pose.

#### Scenario: Five panels with labels
- **WHEN** the renderer runs on a part with 11 labeled features
- **THEN** the PNG is valid, contains the five panels, and every visible feature has a name label with a leader line in at least one panel

#### Scenario: Compass panel names
- **WHEN** the panels are titled
- **THEN** titles use the compass convention (South, West, above, below) and none contains "Front", "Left", "left" or "right"

#### Scenario: Headless rendering
- **WHEN** the renderer runs with no display server and no GPU
- **THEN** it succeeds and imports no OpenGL, EGL or pyrender module

### Requirement: Label anchors and placement are computed
Each feature's anchor SHALL be derived from its recorded delta geometry: the visible mesh point (per-view z-buffer test) nearest the delta centroid. Label boxes SHALL be offset outward from the part silhouette and de-overlapped deterministically so that no two label boxes overlap and none leaves its panel. A feature visible in no panel SHALL get no label and SHALL appear in the legend as `NAME (hidden)`. No label position SHALL be read from a hand-authored table.

#### Scenario: Same input gives the same image
- **WHEN** the renderer runs twice on the same STL and features file
- **THEN** the two PNGs are byte-identical

#### Scenario: Occluded feature
- **WHEN** a feature's anchor is occluded in all five panels
- **THEN** no label is drawn for it and the legend lists `NAME (hidden)`

#### Scenario: Labels do not overlap
- **WHEN** two features project within one label-box width of each other in a panel
- **THEN** their label boxes are moved apart so the boxes do not intersect

### Requirement: Legend maps each name to a description
The image SHALL include a legend with one row per feature in vocabulary order: a swatch in the feature's colour, the name, and a one-line description. The description SHALL be the `description` of the `BUILD_PLAN.json` interface with the same `name` when one exists, otherwise the stage operation and the delta bbox size in mm. Names SHALL be byte-identical to the stage labels in the build script.

#### Scenario: Description from the plan
- **WHEN** a stage label matches an interface `name` that has a `description`
- **THEN** the legend row shows that description verbatim

#### Scenario: Description fallback
- **WHEN** a stage label has no matching interface
- **THEN** the legend row shows the operation and delta size, e.g. `cut, 17 x 56 x 8.5 mm`

### Requirement: Every project gets the labeled preview
`build/build.py` SHALL run the export and the labeled render for each non-copy part script after a successful model build and report each PNG path, writing `preview/<part_id>_design.stl` and `preview/<part_id>_preview_labeled.png`. It SHALL skip a part when the script hash recorded in its features file (`freshness.script_hash`) still matches, SHALL regenerate otherwise, and SHALL NOT fail the build when a preview cannot be produced. `--no-labeled-preview` SHALL skip the step. A project with no stage labels and no positioned interfaces SHALL still produce the image with the five panels, the footer and a legend line `no named features`.

#### Scenario: Fresh STL is not rebuilt
- **WHEN** the recorded script hash matches the part script and the STL and PNG exist
- **THEN** the build reuses them and re-renders nothing

#### Scenario: Project without feature names
- **WHEN** a build script has no `verify_boolean` or `verify_stage` calls and the plan has no positioned interfaces
- **THEN** the PNG is still written with no labels and the legend reads `no named features`
