## Why

`--formats estampo` already emits layer height, infill, and per-part `enable_support` / `brim_type` (the gate's overhang and brim verdicts, replacing Orca's auto brim). Wall loops are the one slicer parameter still left to the user, although the plan's `constraints.wall_min_mm` and the profile's `motion.line_width_mm` fix it.

## What Changes

- `estampo.toml` writes `wall_loops` under `[slicer.orca.overrides]`: `ceil(wall_min_mm / line_width_mm)`, only when both inputs exist.
- The `estampo-export` spec's overrides requirement is corrected: it still says support and brim are never emitted, which the per-part flags already contradict.
- TODO.md item is closed; per-region wall thickness stays under the existing fem TODO.

## Capabilities

### New Capabilities

### Modified Capabilities
- `estampo-export`: slicer overrides requirement gains wall loops and documents the per-part support/brim flags.

## Impact

- `src/estampo_export.py`, `src/deliverables.py` (pass `wall_min_mm` from plan constraints), `tests/test_estampo_export.py`.
- `reference/scripts.md` deliverables row, `TODO.md`.
