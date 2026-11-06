## ADDED Requirements

### Requirement: Phase 1 ends with an SVG concept sketch

At the Phase 1 exit checkpoint the skill SHALL render `sketches/concept.svg` from `sketches/concept.json` using `src/concept_sketch.py` and show it with the dimension table. Phase 2 SHALL NOT start until the user approves the sketch together with the dimensions.

#### Scenario: Sketch shown before planning
- **WHEN** Phase 1 reaches its exit checkpoint
- **THEN** `sketches/concept.svg` exists and is presented, and planning waits for approval

#### Scenario: Sketch corrected
- **WHEN** the user says the sketch misreads the concept
- **THEN** `concept.json` is amended, the SVG is re-rendered, and the correction is recorded in the request log

### Requirement: The sketch renderer is deterministic and validates input

`src/concept_sketch.py` SHALL accept JSON with `title`, `shapes` (rectangles, circles, lines, polylines), `labels` and `dims`, each shape tagged with a view of `front`, `top` or `side`. It SHALL write well-formed SVG and SHALL report a typed error for an unknown shape or view. It SHALL NOT import CadQuery.

#### Scenario: Valid input
- **WHEN** a JSON with one rectangle in the `front` view and one dimension is rendered
- **THEN** the output parses as SVG and contains the dimension text

#### Scenario: Unknown shape
- **WHEN** the JSON contains a shape type outside the list
- **THEN** the exit code is non-zero and the error names the shape

### Requirement: The sketch is a communication aid only

No geometry, parameter or plan value SHALL be derived from the sketch. `regen_prompt.py` SHALL list `sketches/concept.svg` and `concept.json` among the files to re-attach.

#### Scenario: Regeneration lists the sketch
- **WHEN** `REGENERATE.md` is generated for a project with a concept sketch
- **THEN** the sketch paths appear in its file list
