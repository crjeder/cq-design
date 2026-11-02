## Why

`material` is a single plan-level enum, so a part cannot mix e.g. rigid PLA with a TPU grip
or PVA support, and TODO item 8 (multi-color 3MF) only covers color. Real multi-material
printing needs a per-body material, a slicer filament assignment, and planner judgment on
when a second material pays off.

## What Changes

- Add optional `material` (and display `color`) on a part and on a `unions[]` entry,
  resolved union -> part -> plan `material`. The existing plan-level `material` stays the
  default, so single-material plans validate and export unchanged.
- Model every material boundary as non-sticky: nothing in the pipeline assumes adhesion
  between different materials. Touching or overlapping bodies of different materials are
  accepted silently (no error, no warning); PVA support against PLA is the reference case.
- Assign a filament slot per distinct (material, color) automatically; write it to the 3MF
  (`m:colorgroup` color plus Bambu/Orca object-level `extruder` metadata).
- Add `max_materials` (configured filament slots) to the printer profile. When a plan
  needs more distinct materials than slots, the plan summary warns and the planner asks the
  user how to proceed (merge materials, drop one, or confirm a manual swap).
- Planner may suggest a second material when it names a concrete trigger (compliance next
  to rigidity, soluble support, heat zone), and always honors a user request for one.
  Default stays single material.
- Per-part material density in weight estimates; plan summary gains material/color columns.

## Capabilities

### New Capabilities
- `part-materials`: per-part/union material and color, resolution order, slot assignment,
  non-sticky boundary semantics, slot-overflow warning.

### Modified Capabilities
- `model-export`: multi-material 3MF carries color and filament/extruder per body.
- `printer-profile-config`: optional `max_materials` slot count.
- `planning-phase`: when the planner may propose multiple materials and the slot-overflow question.

## Impact

- `src/build_plan_schema.json`, `src/printer_profile_schema.json`, `src/profile.default.json`
- `src/plan.py` (resolution, slot assignment, summary), `src/exporters/threemf_multi.py`,
  `deliverables._write_3mf`, `src/quality_gate.py` (per-body density)
- `prompts/planning.md`; `TODO.md` item 8 superseded; tests under `tests/`.
- Open risk: whether Bambu/Orca need one object with several volumes (not one object per
  union) to treat bodies as one multi-material model. See design.
