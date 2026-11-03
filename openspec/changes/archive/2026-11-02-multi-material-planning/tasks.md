## 1. Spike: slicer 3MF structure

- [x] 1.1 Read BambuStudio `bbs_3mf.cpp` for object/volume extruder keys; record exact names in design.md
- [ ] 1.2 Hand-build a two-material fixture; confirm OrcaSlicer opens it with two filaments assigned (object+volumes vs separate objects)

## 2. Schema and resolution

- [x] 2.1 Add `material`/`color` to part and `unions[]` in `build_plan_schema.json`; add `max_materials` to the printer profile schema and default
- [x] 2.2 Implement union->part->plan resolution and slot assignment in `plan.py`
- [x] 2.3 Tests: resolution order, deterministic slots, single-material plan byte-identical

## 3. Summary and warnings

- [x] 3.1 Add material/color columns and slot-overflow warning to `plan.py summary`
- [x] 3.2 Test: 5 pairs on 4 slots warns; touching materials produce no output

## 4. Export and checks

- [x] 4.1 Extend `write_named_3mf` and `deliverables._write_3mf` with per-body color/filament per spike result
- [x] 4.2 `quality_gate` per-part density (not per-union, see design); `fem_check` skips with reason on multi-material plans
- [x] 4.3 Tests in `tests/test_assembly_and_deliverables.py`: two filaments give two extruder entries; STL/STEP unchanged

## 5. Planner prompt and docs

- [x] 5.1 Update `prompts/planning.md`: default single material, suggestion triggers, non-sticky guidance, slot-overflow question
- [x] 5.2 Update FILES.md, `reference/scripts.md`, and mark TODO.md item 8 superseded
