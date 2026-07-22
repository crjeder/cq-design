## ADDED Requirements

### Requirement: In-script helper detects construction-stage mismatch

The project SHALL provide a helper importable by a generated part script (via the
existing `PYTHONPATH=<src>` the wrapper sets) that checks a Workplane/solid at a
named construction stage against a caller-supplied expected bounding box and/or
minimum volume. At least one of `bbox` or `vol_min` SHALL be supplied. The helper
SHALL raise a `RuntimeError` marked `[cq-verify:stage_mismatch:<label>] ...` when the
supplied bbox does not match within tolerance, or the volume is below `vol_min`. On
success the helper SHALL return the input unchanged so it chains inline like the
existing `verify_boolean`, `verify_feature_bounds`, and `check_workplane` helpers.

#### Scenario: Stage bbox mismatch

- **WHEN** a generated script asserts an expected bounding box for a named stage and
  the actual bbox differs beyond tolerance
- **THEN** the helper raises `RuntimeError` naming the stage `label` and reporting
  expected vs. actual bbox

#### Scenario: Stage volume below minimum

- **WHEN** a generated script asserts a `vol_min` for a named stage and the actual
  solid's volume is below it
- **THEN** the helper raises `RuntimeError` naming the stage `label` and reporting
  the actual volume vs. `vol_min`

#### Scenario: Stage matches expectations

- **WHEN** a stage's bbox and/or volume are within the asserted expectations
- **THEN** the helper returns the input Workplane/solid unchanged without raising

---

### Requirement: Wrapper maps stage mismatch to a typed error

`run_cadquery_model.py` SHALL catch the `[cq-verify:stage_mismatch:<label>]` marked
`RuntimeError` and map it to a `stage_mismatch` entry in the JSON `errors` list,
alongside the existing `silent_boolean`, `feature_overflow`, and `workplane_drift`
typed errors, carrying the stage `label` and mismatch detail in the error message.

#### Scenario: Scratch part script raises a stage mismatch

- **WHEN** a generated part script's subprocess run raises the
  `[cq-verify:stage_mismatch:<label>]` marked error
- **THEN** the wrapper's JSON output includes an `errors` entry with
  `"type": "stage_mismatch"` naming the stage `label`

---

### Requirement: Scratch parts require a staged construction plan

For a part authored from scratch -- no matching block, no matching archetype
template -- the part-generation guidance SHALL require the script to open with an
ordered construction plan: named stages, each asserted via `verify_stage` with an
expected bbox and/or minimum volume, as the script executes. This requirement SHALL
NOT apply to parts built from a block or an archetype template, which already
inherit verified topology.

#### Scenario: Scratch part script includes staged assertions

- **WHEN** a part has no archetype match and is authored as raw fluent CadQuery
- **THEN** the generated script asserts each construction stage via `verify_stage`
  before proceeding to the next stage

#### Scenario: Archetype-based part is exempt

- **WHEN** a part is built by copying and editing an archetype template
- **THEN** the construction-plan requirement does not apply
