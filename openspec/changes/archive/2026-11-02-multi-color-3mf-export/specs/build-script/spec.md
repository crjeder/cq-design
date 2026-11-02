## MODIFIED Requirements

### Requirement: build.py writes named-object 3MF, STL and extra formats

`build.py` SHALL write, per requested format:

- `3mf`: `model.3mf` in which each union without an `object` is a separately named
  object, and each `object` group is one named object whose members are its parts (see
  the `multi-color-export` capability), in print orientation when one is resolved, else
  the assembled pose. Names SHALL derive from the part's `description` (whitespace
  collapsed, control characters removed, length bounded), falling back to the part `id`
  when empty, and SHALL be disambiguated with the part `id` suffix only for colliding
  names; a group's parts SHALL be named by their union ids. Each object SHALL carry its
  `plate` tag as metadata. Distinct unions SHALL NOT be fused, and the written 3MF SHALL
  have no non-manifold edges.
- `stl`: one STL per union in the assembled pose and one fused print-pose STL per plate
  holding more than one union.
- `step`, `obj`, `iges`, `scad`: one `<union-id>.<ext>` per union in the assembled pose.
  Keep-out zones SHALL NOT be written in any user-facing format.

#### Scenario: Each union is a named 3MF object

- **WHEN** a model with multiple unions, none declaring `object`, is built with `--formats 3mf`
- **THEN** each union is a separately named object with its plate in metadata, and no two are fused

#### Scenario: An object group is one 3MF object

- **WHEN** two unions share `object: "knob"` and `--formats 3mf` runs
- **THEN** `model.3mf` holds one object for the group with two unfused parts named after the union ids

#### Scenario: Per-union STL plus fused plate STL

- **WHEN** a plate holds two print-in-place unions and `--formats stl` runs
- **THEN** one STL per union and one fused STL for the plate are written

#### Scenario: Keep-out zones are not deliverables

- **WHEN** a part declares a keep-out zone and any format is built
- **THEN** no file for the zone appears in `--out`
