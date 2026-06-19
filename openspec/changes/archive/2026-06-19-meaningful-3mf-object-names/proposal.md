## Why

Exported 3MF objects carry unhelpful names: a slicer operator opening `model.3mf`
sees generic placeholders like `CadQuery Shape 0` (or, at best, the terse snake_case
part id) with no indication of what each object is. The build plan already holds a
human-readable `description` per part; surfacing it as the object name lets the
operator identify each union at a glance when re-distributing objects across plates.

## What Changes

- The model exporter derives each 3MF object's `name` attribute from the part's
  `description` in `BUILD_PLAN.json` instead of the part `id`.
- A description is sanitized into a valid, readable object name (trimmed, control
  characters and XML-hostile characters removed, length-capped) before it is written.
- The part `id` remains the stable identifier for STL filenames, plate grouping, and
  the kinematic check; only the human-facing 3MF object name changes.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `model-export`: the requirement that unions export as separately named objects is
  tightened to specify that the object name is derived from the part `description`,
  not the part `id` or a kernel-generated placeholder.

## Impact

- Code: `src/model_export.py` (name passed to `write_named_3mf`); a small name-
  sanitizing helper. `src/exporters/threemf_multi.py` already accepts an arbitrary
  `name` and needs no change to its contract.
- Tests: `tests/test_model_export.py` gains an assertion that object names match the
  sanitized part descriptions.
- No schema change: `description` is already a required field on every part.
