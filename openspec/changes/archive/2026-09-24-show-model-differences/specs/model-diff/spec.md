## ADDED Requirements

### Requirement: Model diff summary
`src/diff_models.py` SHALL accept two watertight STL paths and emit a JSON object with `success`, `errors`, `volume_a`, `volume_b`, `only_a_volume`, `only_b_volume`, `common_volume`, `bbox_delta`, `identical`, and `png`.

#### Scenario: Different models
- **WHEN** B is A with a 10 mm cube added
- **THEN** `only_b_volume` is 1000 (within tolerance), `only_a_volume` is 0, and `identical` is false

#### Scenario: Identical models
- **WHEN** both paths hold the same mesh
- **THEN** `identical` is true and both only-volumes are 0

#### Scenario: Unusable input
- **WHEN** either mesh cannot be loaded or is not watertight
- **THEN** `success` is false, `errors` has a typed entry with `type`, `message`, `hint`, and the exit code is 1

### Requirement: Diff preview image
With `--png <path>`, the tool SHALL write an image showing common geometry in gray, geometry only in A in red, and geometry only in B in green.

#### Scenario: PNG written
- **WHEN** `--png out.png` is passed for two differing models
- **THEN** `out.png` exists and `png` in the JSON is its path
