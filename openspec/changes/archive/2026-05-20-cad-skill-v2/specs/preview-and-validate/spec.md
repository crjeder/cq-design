## MODIFIED Requirements

### Requirement: Wrapper JSON includes geometry metrics
The wrapper SHALL include a `geometry` object in its JSON output whenever a model script runs successfully and produces geometry (regardless of whether `--preview` is set).

The `geometry` object SHALL contain:
- `bbox`: object with `x_mm`, `y_mm`, `z_mm` (bounding box extents)
- `volume_cm3`: number (model volume in cubic centimetres)
- `weight_g`: number (estimated weight at PLA density 1.24 g/cm³)
- `face_count`: integer (number of mesh triangles)

#### Scenario: Successful run without preview
- **WHEN** `run_cadquery_model.py model.py` is called without `--preview`
- **THEN** JSON output contains a populated `geometry` object alongside `success: true`

#### Scenario: Failed run
- **WHEN** the model script exits non-zero
- **THEN** `geometry` is `null` in the JSON output

---

### Requirement: Wrapper JSON includes a top-level errors array
The wrapper SHALL include an `errors` array in all JSON output (empty on clean success, populated on failure or DFM warnings). This field SHALL always be present.

#### Scenario: Clean run
- **WHEN** script succeeds, mesh is watertight, no DFM issues
- **THEN** JSON contains `"errors": []`

#### Scenario: Non-watertight mesh without --strict
- **WHEN** mesh is not watertight and `--strict` is not set
- **THEN** `errors` contains a warning entry and `success` remains `true`

---

### Requirement: STL fields are null during iteration, populated only at delivery
The `stl` and `stls` fields in the wrapper JSON SHALL be `null` / `[]` during normal iteration runs. They SHALL only be populated when the wrapper is invoked with `--deliver` flag, which triggers the modular exporter.

#### Scenario: Iteration run
- **WHEN** wrapper runs during orchestration loop (no `--deliver`)
- **THEN** `"stl": null`, `"stls": []` in JSON output

#### Scenario: Delivery run
- **WHEN** wrapper is invoked with `--deliver --formats stl,3mf`
- **THEN** exporter runs, `stls` contains paths to the produced files
