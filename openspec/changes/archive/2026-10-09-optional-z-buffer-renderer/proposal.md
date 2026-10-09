## Why

`preview.py` rendered with matplotlib mplot3d, which has no z-buffer and depth-sorts whole triangles (painter's algorithm). Flat faces showed cosmetic triangular shading patches where wall/fillet triangles painted over coplanar ones. The geometry was correct, but the artifact misled visual review (TODO: "Preview: z-buffered renderer").

## What Changes

- Add `src/zbuffer.py`: a numpy software rasterizer (per-pixel depth test, flat shading with the same light/colors as before). It needs no OpenGL, EGL, osmesa or new dependency.
- **BREAKING (cosmetic):** `preview.py` uses it for every view, replacing the matplotlib mplot3d path. There is no renderer flag. The isometric panel is now orthographic (matplotlib's was mildly perspective), and framing is fitted to the projected bounding box.
- Callout badges are drawn with PIL on the rendered panel using the rasterizer's own projection.
- Remove the stale "see TODO" comment; mark the TODO entry done.

## Capabilities

### New Capabilities

### Modified Capabilities
- `cq-preview-rendering`: rendering uses a z-buffered rasterizer instead of matplotlib, keeping the no-OpenGL / no-display guarantee.

## Impact

- `src/preview.py`, new `src/zbuffer.py`; `reference/scripts.md`, `CLAUDE.md` file layout, `TODO.md`.
- No dependency changes (matplotlib stays: `diff_models.py` still uses it). `run_cadquery_model.py` JSON contract unchanged.
- Tests: `tests/test_preview.py` updated (one detail-view test re-centered; z-buffer test added).
