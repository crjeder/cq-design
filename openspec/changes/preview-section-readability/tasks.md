## 1. Z-buffer depth and edges

- [ ] 1.1 Add `rasterize_with_depth` to `src/zbuffer.py` returning image and depth buffer; keep `rasterize` unchanged
- [ ] 1.2 Add depth-discontinuity edge mask and draw it in `_render_cq_view` (tile, section, detail)
- [ ] 1.3 Test edges on a stepped-plate fixture in `tests/`

## 2. Section caps and informative flag

- [ ] 2.1 Colour cap triangles (on the cut plane) distinctly and outline them in `render_section` / `render_detail_section`
- [ ] 2.2 Compute `informative` from cap vs uncut silhouette masks; return it and print it in `render_preview.py`
- [ ] 2.3 Tests: solid block cut = false, bore cut = true, cap colour differs from coplanar-normal face

## 3. Callout visibility

- [ ] 3.1 Add z-buffer visibility test and panel selection (ortho first, then iso) in `preview.py`
- [ ] 3.2 Merge badges within 12 px; legend `NAME xN` and `NAME (hidden)`
- [ ] 3.3 Tests: occluded anchor, hidden anchor, 4 coincident anchors

## 4. Prompt and docs

- [ ] 4.1 Update `prompts/builder.md`: run validate command verbatim, add-only
- [ ] 4.2 Update `reference/scripts.md`; re-render the storage-shelf case and check the section shows the U profile
