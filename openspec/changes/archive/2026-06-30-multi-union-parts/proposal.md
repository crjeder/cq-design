## Why

The `printable-unit-model` spec already names the *union* -- one rigid body -- as the unit of
motion, export, and kinematic checking, and says "each union declares its `plate`." But the
implementation ties a union 1:1 to a part/script: `union id == part id == script name`, used as the
3MF object name, the `<id>.stl` filename, `kinematics.moving_union`, and the plate-grouping key. A
single script can only yield one union: `model_export` `makeCompound`s all of a part's solids into
one named object.

So a print-in-place hinge -- which the spec describes as "two unions on one plate" -- cannot be
authored as one self-contained block that builds both leaves in one coordinate frame. The human must
split it into two independent parts and re-assert their relationship by hand. The same wall blocks
the broader joint-contract direction (a block owning both members of a joint) explored in the
`joint-contract` design note: it depends on exactly this mechanism.

This change makes **`union` a first-class plan entity distinct from `part`/`script`**: a build unit
(one script) may produce 1..N named unions. `union id = part id` becomes the N=1 default, so every
existing plan and script is unchanged.

## What Changes

- **A part may declare the unions it produces.** A part gains an optional `unions` array; each entry
  declares a globally-unique union `id` and an optional `plate`. Absent `unions` SHALL mean the part
  is a single union whose id is the part id and whose plate is the part's `plate` (today's behavior).
- **A script binds geometry to each union by name.** A part script's top-level `result` MAY be a
  `dict` mapping union id -> CadQuery `Workplane`, with keys exactly the part's declared union ids;
  a plain `Workplane` SHALL remain a single union (id = part id). `result` loading, the DFM wrapper,
  and the preview renderer SHALL accept both shapes.
- **The pipeline keys off unions, not parts.** `model_export` SHALL emit one named 3MF object and one
  `<union_id>.stl` per union (splitting a `dict` result instead of compounding it), apply the part's
  `placement` to each of its unions, and group plates per union. The kinematic and plate-clearance
  stages -- which already operate on per-union meshes and a plate-grouping key -- SHALL enumerate the
  full union set (parts expanded by their `unions`).
- **Plate moves to the union level.** Plate membership is resolved per union (`union.plate`, else the
  part's `plate`, else the union id), so a multi-union block's unions can sit on different plates --
  "printed separate, even on different plates."
- **Validation gains a union namespace.** `plan_validate` SHALL enforce union-id uniqueness across the
  model, that every part script's `result` dict keys equal its declared `unions`, and that
  `kinematics.moving_union` and plate references resolve against union ids.

## Capabilities

### Modified Capabilities
- `printable-unit-model`: a build unit (part/script) may declare and produce multiple named unions;
  union ids form the namespace that motion, plate, and export reference; plate is per union; the
  single-union (id = part id) case is the default.

(`model-export` is touched in **implementation** -- it splits a part's union-keyed `result` per union
instead of compounding a part into one object -- but its spec requirements are already union-centric
("each union is a separately named object", "one STL per union") and need no change.)

## Impact

- Plan schema: `src/build_plan_schema.json` -- add the part `unions` array; document plate-per-union.
- Result contract: `src/exporters/__init__.py` (`_load_result` returns `Workplane | dict`),
  `src/run_model_shim.py`, `src/run_cadquery_model.py` (DFM wrapper validates each union body),
  `src/render_preview.py` (preview a dict result).
- Export/checks: `src/model_export.py` (split + per-union plate + cross-check), and the union
  enumeration consumed by `src/kinematic_check.py` and `src/plate_clearance_check.py` (parts expanded
  to unions). A shared "iterate unions of the plan" helper centralizes the part->unions expansion.
- Validation: `src/plan_validate.py` -- union-namespace checks.
- Specs: `printable-unit-model` (modified), `model-export` (modified). The kinematic/plate specs need
  no requirement change (they already say "every other union" / per-union); only the union
  enumeration generalizes.
- Tests: a part declaring two unions exports two named objects + two STLs on (optionally) two plates;
  a single-Workplane part is byte-identical to today; `plan_validate` rejects duplicate union ids and
  a `moving_union` that names no union.
- Out of scope: the joint *contract* / satisfaction algebra (the `joint-contract` D1 crux), and
  annotation (mating-area / assembly-envelope) geometry. This change is the union-production plumbing
  those later ride on. Per-union `placement` (each union posed independently) is also out of scope --
  a part's unions share its placement, built in one frame.
