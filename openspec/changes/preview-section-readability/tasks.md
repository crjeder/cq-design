## 1. Z-buffer depth and edges

- [x] 1.1 Add `rasterize_with_depth` to `src/zbuffer.py` returning image and depth buffer; keep `rasterize` unchanged
- [x] 1.2 Add depth-discontinuity edge mask and draw it in `_render_cq_view` (tile, section, detail)
- [x] 1.3 Test edges on a stepped-plate fixture in `tests/`

## 2. Section caps and informative flag

- [x] 2.1 Colour cap triangles (on the cut plane) distinctly and outline them in `render_section` / `render_detail_section`
- [x] 2.2 Compute `informative` from cap vs uncut silhouette masks; return it and print it in `render_preview.py`
- [x] 2.3 Tests: solid block cut = false, bore cut = true, cap colour differs from coplanar-normal face

## 3. Callout visibility

- [x] 3.1 Add z-buffer visibility test and panel selection (ortho first, then iso) in `preview.py`
- [x] 3.2 Merge badges within 12 px; legend `NAME xN` and `NAME (hidden)`
- [x] 3.3 Tests: occluded anchor, hidden anchor, 4 coincident anchors

## 4. Prompt and docs

- [x] 4.1 Update `prompts/builder.md`: run validate command verbatim, add-only
- [x] 4.2 Update `reference/scripts.md`; re-render the storage-shelf case and check the section shows the U profile
