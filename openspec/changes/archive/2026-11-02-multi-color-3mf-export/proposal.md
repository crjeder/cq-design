## Why

Multi-toolhead printers (Snapmaker U1, Bambu AMS) can print one part in several
filaments, but every union cq-design exports becomes its own slicer object, so a
two-color part has to be reassembled and recolored by hand in the slicer. Orca-family
slicers already read a per-part filament assignment from a Bambu-style project 3MF, and
`threemf_multi.py` already writes the companion `Metadata/model_settings.config` for
plates, so the gap is small. Separately, Snapmaker Orca only honors that config when the
3MF's `Application` metadata starts with `BambuStudio-` or `Snapmaker_Orca-`; ours says
`OrcaSlicer-2.3.0`, so Snapmaker Orca silently drops our plate layout today.

## What Changes

- Union entries in `BUILD_PLAN.json` gain two optional fields: `object` (a group id;
  unions sharing it are exported as the bodies of one slicer object) and `filament`
  (1-based filament slot / extruder number for that body).
- Plan validation enforces that the members of one `object` come from the same part
  and share one plate, and that `filament` is an integer >= 1. The plan-level
  `material` stays single-valued: all bodies are the same material in different colors.
- `model.3mf` writes each `object` group as one 3MF object built from `<components>`,
  with each member's mesh in its own `3D/Objects/object_<n>.model` file (Bambu layout,
  3MF production extension, `p:path`), and `Metadata/model_settings.config` carries a
  `<part>` with an `extruder` metadata entry per member. Ungrouped unions keep today's
  inline single-mesh objects, and also get an object-level `extruder` when `filament` is set.
- The 3MF `Application` metadata changes from `OrcaSlicer-2.3.0` to a `BambuStudio-`
  prefixed string, so both OrcaSlicer and Snapmaker Orca apply plate and filament
  assignments.
- The plate-clearance gate skips pairs of unions in the same `object` (they touch by
  design) and instead requires them to be disjoint: a positive overlap volume between
  two members of one object is a blocking `object_member_overlap` issue.
- No filament presets or colors are written (`project_settings.config` is not emitted).
  If a `filament` number exceeds the slots configured in the user's slicer project, the
  slicer shows it and the user resolves it there.

## Capabilities

### New Capabilities
- `multi-color-export`: plan fields for grouping unions into one multi-body slicer
  object with a per-body filament slot, their validation, and how they are written into
  the Bambu-style 3MF (components, per-part extruder, generator string).

### Modified Capabilities
- `build-script`: the named-object 3MF requirement changes from "each union is its own
  object" to "each ungrouped union, and each `object` group, is one named object".
- `plate-clearance-validation`: co-plated unions in the same `object` are exempt from the
  clearance threshold and must instead be disjoint.

## Impact

- Code: `src/build_plan_schema.json`, `src/plan.py` (validation), `src/units.py` (`iter_unions`),
  `src/exporters/threemf_multi.py`, `src/deliverables.py`, `src/plate_clearance_check.py`
  (using `src/interference.py`), skill text in `skill/phase2_planning.md` and
  `skill/phase4_deliver.md`, `reference/scripts.md`.
- Tests: `tests/test_plan.py`, the 3MF exporter tests, the plate-clearance tests.
- Out of scope: mixing different materials (bonding/interface rules, TODO "Engineering
  of multi-material interfaces"), triangle painting (`paint_color`), filament color
  presets, preview tinting.
