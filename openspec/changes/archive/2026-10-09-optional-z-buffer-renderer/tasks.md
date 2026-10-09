## 1. Rasterizer

- [x] 1.1 Add `src/zbuffer.py`: orthographic camera from (elev, azim) matching matplotlib's convention, `rasterize`, 2x supersampling
- [x] 1.2 Add test in `tests/test_preview.py`: uniform flat-face color, occlusion changes silhouette

## 2. Integration

- [x] 2.1 Vectorize `_shade_triangles` in `src/preview.py`
- [x] 2.2 Replace the matplotlib path in `_render_cq_view`; draw callouts with PIL via the zbuffer projection
- [x] 2.3 Fix `tests/test_preview.py` detail-zoom test for the new framing; full preview + wrapper tests pass

## 3. Docs

- [x] 3.1 Update `reference/scripts.md` and `CLAUDE.md` (preview.py description, add `zbuffer.py`)
- [x] 3.2 Mark the TODO.md entry done and update openspec/specs wording if present
