## 1. Reference file

- [x] 1.1 Derive the reference layout from the OrcaSlicer and Snapmaker Orca `bbs_3mf.cpp` importer/exporter source (`main`, 2026-10-24) instead of a saved file: component `p:path` resolved via `3D/_rels/3dmodel.model.rels`, `<part id>` = component object id, per-part `extruder` metadata
- [x] 1.2 Record from it the `Application` version token and whether the grouped `<object>` carries its own `extruder` metadata; resolve both open questions in `design.md`

## 2. Plan schema and validation

- [x] 2.1 Add optional `object` (string) and `filament` (integer >= 1) to union entries in `src/build_plan_schema.json`
- [x] 2.2 Validate in `src/plan.py`: object members from one part, one resolved plate, at least two members; structured errors naming object, parts/plates
- [x] 2.3 Add a helper next to `units.iter_unions` returning `{object_id: [union_id, ...]}` for the exporter and gate to share
- [x] 2.4 Tests in `tests/test_plan.py` for each validation scenario in `specs/multi-color-export/spec.md`, including `filament: 0` rejection and plans without the fields

## 3. 3MF writer

- [x] 3.1 Change `_GENERATOR_APPLICATION` in `src/exporters/threemf_multi.py` to the `BambuStudio-` token from 1.2
- [x] 3.2 Extend `write_named_3mf` to take object groups: write member meshes to `3D/Objects/object_<n>.model`, a root `<components>` object with `p:path`, the production namespace + `requiredextensions="p"`, and `3D/_rels/3dmodel.model.rels`
- [x] 3.3 Emit `<object>` / `<part>` entries with `name` and `extruder` metadata in `Metadata/model_settings.config`, keeping `<plate>` entries; plate `model_instance` references the root object id
- [x] 3.4 Write ungrouped unions that declare `filament` as one-part component objects with object-level `extruder` (the importer ignores a single volume's own extruder)
- [x] 3.5 Keep the non-manifold guard: count per member mesh file and sum
- [x] 3.6 Tests: structure matches the reference layout from 1.1, extruders written per part, ungrouped output unchanged except the generator string

## 4. Deliverables wiring

- [x] 4.1 In `src/deliverables._write_3mf`, build groups from the helper in 2.3; members share the first member's print orientation and keep relative pose (same rule as co-plated clusters)
- [x] 4.2 Name the group object from the part `description` via `_dedupe_object_names`, parts by union id
- [x] 4.3 Test in `tests/test_assembly_and_deliverables.py`: a two-union grouped part builds one 3MF object with two parts; STL/STEP outputs per union unchanged

## 5. Plate-clearance gate

- [x] 5.1 In `src/plate_clearance_check.py`, skip the clearance threshold for pairs sharing an `object`
- [x] 5.2 For those pairs, measure `interference._intersection_volume` and emit `object_member_overlap` errors above 0.1 mm^3
- [x] 5.3 Tests in `tests/test_plate_clearance_check.py`: touching members pass, overlapping members fail, non-grouped pairs unchanged

## 6. Skill text and docs

- [x] 6.1 `prompts/planning.md` rule 6b: when to use `object`/`filament` (color regions as disjoint unions from one script, same plate)
- [x] 6.2 `prompts/part.md` rule 3 + `{{UNIONS}}` shows each union's object: author color regions as disjoint solids (cut one from the other) returned in the `result` dict
- [x] 6.3 `skill/phase4_deliver.md`: tell the user filament slots are preassigned and to map slot colors in the slicer
- [x] 6.4 Update `reference/scripts.md` (3MF layout, new gate issue type) and `FILES.md`
- [x] 6.5 Tick the `Multi color / material support` TODO item to color-only done; leave material interfaces open

## 7. Manual verification

- [ ] 7.1 Open a built two-color `model.3mf` in OrcaSlicer and Snapmaker Orca: one object, two parts on extruders 1 and 2, plates applied
- [x] 7.2 Run `uv run pytest tests/` and `ruff check` / `ruff format` on changed files
