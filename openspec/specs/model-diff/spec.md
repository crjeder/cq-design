# Spec: model-diff

## Purpose

Compare two watertight STL meshes and report or render what was removed and added between them.

## Requirements

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

### Requirement: Localization and volume checks
`src/diff_models.py` SHALL accept `--region xmin,ymin,zmin,xmax,ymax,zmax`, `--expect-volume LO,HI` and `--outside-tol REL` (default 0.005). The JSON SHALL always carry `outside_volume`, `changed_bbox`, `volume_delta`, `localized`, `volume_in_range` and `region_fraction`. With `--region`, `outside_volume` SHALL be the volume of the only-A and only-B material lying outside the box, `localized` SHALL be true when `outside_volume <= outside_tol * volume_a`, and `region_fraction` SHALL be the region's overlap with A's bounding box divided by that bounding box's volume. `changed_bbox` SHALL be the bounds of the only-A and only-B material, or null when there is none. `volume_delta` SHALL be `only_b_volume - only_a_volume`. With `--expect-volume`, `volume_in_range` SHALL be true when `LO <= volume_delta <= HI`. A check whose flag is absent SHALL report null. These checks SHALL NOT change `success`, `errors` or the exit code.

#### Scenario: Change inside the region
- **WHEN** B is A with a 10 mm cube added and `--region` encloses the cube
- **THEN** `localized` is true and `outside_volume` is 0

#### Scenario: Collateral change outside the region
- **WHEN** B is A with a cube added inside the region and a second cube added outside it
- **THEN** `localized` is false and `outside_volume` equals the second cube's volume

#### Scenario: Volume out of range
- **WHEN** the diff adds 1000 mm3 and `--expect-volume 2000,3000` is passed
- **THEN** `volume_in_range` is false and `volume_delta` is 1000

#### Scenario: Checks not requested
- **WHEN** neither flag is passed
- **THEN** `localized` and `volume_in_range` are null and the other keys keep their previous values

#### Scenario: Region covers the model
- **WHEN** `--region` equals A's bounding box
- **THEN** `region_fraction` is 1
