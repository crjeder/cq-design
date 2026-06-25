## Why

The named-object 3MF is the whole point of `model_export`: each union becomes a separately
named object so a slicer operator can tell them apart on the plate. But the names are not
deduplicated. `model_export.py:94-101` derives every object's name from the part's
`description` via `_object_name(description, part["id"])`, and when two parts carry the same
`description` they get the **same** object name. To the operator the objects are then
indistinguishable -- which defeats the named-object feature exactly when it matters most
(e.g. a model with two "Hinge leaf" parts, or several "Bracket" copies). The build plan
makes no guarantee that descriptions are unique, so this is reachable from ordinary plans,
not just hostile input.

`_object_name` already falls back to the part `id` (which is unique) when the sanitized
description is empty, so the empty case is fine; the gap is two parts with the *same
non-empty* description.

## What Changes

- **Guarantee unique 3MF object names.** The exporter SHALL ensure no two objects in the
  named 3MF share a name. When two or more parts would otherwise produce the same name, the
  exporter SHALL disambiguate by suffixing each colliding object's name with its part `id`
  (which the schema already guarantees is unique).
- **Leave non-colliding names unchanged.** A part whose name does not collide with any other
  SHALL keep its plain sanitized description, so the common case is unaffected and existing
  output does not churn.

## Capabilities

### Modified Capabilities
- `model-export`: the requirement that objects are named from the part description is
  extended to also guarantee names are unique across the 3MF, disambiguating collisions by
  suffixing the part id.

## Impact

- Tooling: `src/model_export.py` -- add a name-deduplication pass over the per-part object
  names before `write_named_3mf` (around `model_export.py:94-101`); the `_object_name`
  helper itself is unchanged.
- Specs: `model-export` (modified delta) -- add a uniqueness clause and a collision scenario
  to the existing "Unions export as separately named objects" requirement.
- Tests: `tests/test_model_export.py` -- two parts with identical descriptions yield two
  distinct object names, each carrying its part id; a single part / all-distinct
  descriptions are unchanged.
- Out of scope: changing the `_object_name` sanitization rules, the length cap, or the
  empty-description fallback; and any change to STL/plate naming (those are keyed on the
  already-unique part id and plate id).
