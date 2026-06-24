## Why

The current print-orientation support score counts downward overhang area as a flat
sum above the angle limit, so a marginal 46-degree overhang and a near-horizontal
89-degree overhang of equal area score identically even though the latter needs far
more support. Candidate enumeration also leans on convex-hull facets, which fragment
on organic meshes, and there is no objective for minimizing build height (print time,
toppling risk). The Tweaker-3 project demonstrates better-behaved heuristics; we adopt
its documented formulas (clean-room reimplementation) without taking its GPL-3.0 code,
keeping this project under PolyForm Noncommercial.

## What Changes

- Add a **severity-weighted support cost** for orientation ranking: each downward face
  contributes by how far it leans past the overhang limit, raised to an exponent, so
  steeper overhangs dominate. Exposed as a new metric used only by orientation scoring;
  the quality gate's reported `overhang_area_mm2` (true physical area) is unchanged.
- Add **area-cumulation candidate generation** as a supplement to the existing
  convex-hull + axis-aligned candidate set: accumulate face-area-weighted normals and
  take the top-N, giving a bounded, area-prioritized candidate set on dense/organic meshes.
- Add a **`min_build_height` optimization objective**: select the orientation that
  minimizes the posed bounding-box Z extent, with the existing scores as tiebreakers.
- Use a **first-layer-height band** for bed-contact detection instead of the current
  tight `CONTACT_Z_EPS_MM`, so a slightly non-coplanar resting face still counts as
  contact (matches FDM first-layer behavior).

No GPL code or Tweaker-3's evolutionarily-tuned constants are copied; the exponent and
band defaults are derived/tuned independently.

## Capabilities

### New Capabilities
<!-- none: all changes refine the existing print-orientation capability -->

### Modified Capabilities
- `print-orientation-optimization`: candidate enumeration gains an area-cumulation
  source; the support score becomes severity-weighted; bed contact uses a first-layer
  band; a `min_build_height` objective is added.

## Impact

- Code: `src/print_orientation.py` (candidate enumeration, support metric, new mode,
  bed-contact band), `src/mesh_io.py` (new severity-weighted support-cost helper
  alongside the unchanged `overhang_metrics`).
- Tests: `tests/test_print_orientation.py`, `tests/test_mesh_io.py`.
- Dependencies: none added (numpy + trimesh already present).
- Licensing: clean-room reimplementation; no Tweaker-3 (GPL-3.0) source or tuned
  constants included. Project stays under PolyForm Noncommercial.
- Out of scope: `overhang-analysis` (quality-gate reporting) is unaffected; the wrap
  Tweaker-3-as-external-MCP option is explicitly not pursued.
