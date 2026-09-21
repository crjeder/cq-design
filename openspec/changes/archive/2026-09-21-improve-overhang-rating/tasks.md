## 1. Profile

- [x] 1.1 Add optional `constraints.bridge_max_mm` (min 0) to `src/printer_profile_schema.json`; add 10.0 to `src/printer_profile.default.json`
- [x] 1.2 Test in `tests/test_printer_profile_validate.py`: absent OK, negative rejected

## 2. Region-based overhang analysis (mesh_io)

- [x] 2.1 Add `overhang_regions()` (connected components of selected faces) and bridge classification in `src/mesh_io.py`
- [x] 2.1a Add support-side test: anchored boundary edges (neighbor face is wall/up-facing) binned to the 4 sides of the oriented rectangle; require >= 2 sides each >= 50% covered
- [x] 2.2 `overhang_metrics(mesh, overhang_deg, bridge_max_mm=10.0)`: exclude bridges from `overhang_area_mm2` and worst face; add `bridge_area_mm2`, `bridge_count`
- [x] 2.3 `support_cost`: per-region continuous ramp with `OV_H`, bridge factor 0.1
- [x] 2.4 Single shared bed-contact helper using `FIRST_LAYER_BAND_MM`; use in `overhang_metrics` and `print_orientation._bed_contact_mask`
- [x] 2.5 Tests: short bridge vs long span vs one-sided cantilever ledge (steep narrow overhang case not covered); tessellation invariance (<1%); no cliff at the limit

## 3. Consumers

- [x] 3.1 `print_orientation.py`: pass `bridge_max_mm` from profile, rename `SUPPORT_EXPONENT` to `OV_H` (keep alias), deterministic tie-break ordering
- [x] 3.2 `quality_gate.py`: read `bridge_max_mm`, bridge-only parts emit no `overhang_exceeded`; emit an `info` `bridges_detected` issue carrying `bridge_area_mm2`
- [x] 3.3 Tests: `tests/test_print_orientation.py` (bridge does not drive pose; repeat-run determinism), `tests/test_quality_gate.py` (bridge-only part clean)

## 4. Docs and verification

- [x] 4.1 Update `reference/scripts.md` JSON shapes; tick TODO.md defect and `OV_H` / `FIRST_LAY_H` items
- [ ] 4.2 Run `uv run pytest tests/` (done: no failures; 18 collection/fixture errors pre-exist at HEAD, conftest lacks `tmp_stl`/`run_wrapper`/`minimal_plan`); check `evals/` orientation shifts (not done: run_evals needs a generated --run-dir)
