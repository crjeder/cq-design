## Why

The current preview renderer produces six exterior views, which makes it impossible to verify internal geometry: hollow walls, screw bosses, snap hooks, port cutouts, and voids are completely hidden. Designers using the cq-design skill have no way to confirm internal DFM details are correct without exporting and opening in a full CAD viewer.

## What Changes

- `preview.render_multi_view` gains an optional `cross_sections` parameter (default `False`) that, when enabled, appends up to three cross-section views (XY, XZ, YZ planes through the model centroid) to the output PNG tile.
- `render_preview.py` CLI gains a `--cross-sections` flag that passes through to the renderer.
- `run_cadquery_model.py` passes `--cross-sections` to `render_preview.py` when invoked with `--preview --cross-sections`.
- The cross-section views are rendered using CadQuery's `.cut()` against a half-space solid, then tessellated with the same OCC/matplotlib pipeline -- no new OpenGL dependency introduced.

## Capabilities

### New Capabilities

- `preview-cross-sections`: Cross-section slice views appended to the multi-view preview tile, cutting through the model centroid on XY, XZ, and YZ planes.

### Modified Capabilities

- `cq-preview-rendering`: `render_multi_view` and the `render_preview.py` CLI gain opt-in cross-section support; the scenario for "six-view PNG" must expand to cover the cross-section tile option.

## Impact

- `src/preview.py`: new `cross_sections` parameter on `render_multi_view` and `render_single`.
- `src/render_preview.py`: new `--cross-sections` CLI flag.
- `src/run_cadquery_model.py`: forwards `--cross-sections` when present.
- No new package dependencies (CadQuery BRep Boolean ops are already available via OCC).
- Existing six-view behavior unchanged when `cross_sections=False` (the default).
