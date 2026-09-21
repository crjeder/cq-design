## Why

`mesh_io.overhang_metrics` and `mesh_io.support_cost` score overhangs per triangle. A short
horizontal bridge (which prints fine) is counted as a full overhang, so the quality gate raises
`overhang_exceeded` on it and print-orientation picks poses that avoid harmless bridges
(TODO Defects: "bridges are treated as overhangs"). The per-triangle score is also unstable:
it changes with tessellation density, jumps at the `overhang_deg` threshold and at the bed-contact
height band, so tiny geometry edits can flip the chosen orientation.

## What Changes

- Group down-facing over-limit faces into connected regions (edge adjacency) and score per region, not per triangle. Score becomes tessellation-invariant.
- Classify a near-horizontal region as a **bridge** when its shortest in-plane extent is <= `bridge_max_mm` and it is supported on at least two sides; bridges are reported separately and excluded from the overhang findings and from the support cost (or heavily discounted, see design).
- Add printer constraint `bridge_max_mm` (default 10.0) to `printer_profile.json` (optional in schema).
- Replace the hard threshold in the support cost with a continuous severity ramp (progressive penalty, exponent `OV_H`), so faces just past the limit cost near zero instead of a step.
- Make orientation ranking deterministic: ties within a band fall to a fixed key order, and the bed-contact test uses a first-layer band rather than a tight epsilon.
- `overhang_metrics` gains `bridge_area_mm2` and `bridge_count`; existing keys keep their names and meaning.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `overhang-analysis`: bridges of span <= `bridge_max_mm` are not overhangs; overhang area is region-based.
- `print-orientation-optimization`: support score is region-based, bridge-aware, continuous, and deterministic.
- `printer-profile-config`: new optional `constraints.bridge_max_mm`.

## Impact

- `src/mesh_io.py` (`overhang_metrics`, `support_cost`, new region helper)
- `src/print_orientation.py` (`_support_metrics`, constants)
- `src/quality_gate.py` (reads new fields; bridge-only parts no longer emit `overhang_exceeded`)
- `src/printer_profile_schema.json`, `src/printer_profile.default.json`
- `reference/scripts.md` (JSON shapes), `TODO.md` (tick defect + Tweaker items `OV_H`, `FIRST_LAY_H`)
- Tests: `tests/test_print_orientation.py`, `tests/test_quality_gate.py`, mesh_io overhang tests. Golden evals may shift orientation choices.
