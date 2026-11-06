## Why

Section and orthographic previews are flat-Lambert shaded with no edges, so a cut cap, a
base-plate top and a channel floor (all +z normal) render as one colour. A real z=72 cut
of a storage shelf came out as a uniform blue rectangle and both audits passed on it
(TODO.md "Cross-sections show nothing", "Labels where the features cannot be seen").
Callout badges are projected without a visibility test, so they point at hidden features
and pile up. Automatic feature and section selection (follow-up change
`preview-feature-frames`) would only produce more blank images until this is fixed.

## What Changes

- Section renders draw the cap (triangles on the cut plane) in a distinct colour with an outline.
- All panels (ortho tile, sections, details) get silhouette/depth-discontinuity edge lines
  derived from the existing z-buffer.
- `render_section` / `render_detail_section` report `informative: false` when the cap
  silhouette equals the uncut silhouette (no hole, notch or void).
- Callout anchors get a z-buffer visibility test; each callout picks the first panel (ortho
  panels, then isometric) where its anchor is visible; badges projecting within a few
  pixels of each other merge ("rim_rails x4"); a callout visible in no panel is listed
  "hidden" in the legend.
- The builder prompt uses the rendered validate command verbatim: it may add cuts, not replace them.

## Capabilities

### New Capabilities

### Modified Capabilities
- `preview-cross-sections`: cap colour + outline, edge lines, `informative` flag, verbatim-command rule.
- `preview-feature-callouts`: visibility-tested placement across panels, badge merging, "hidden" legend state.

## Impact

- `src/zbuffer.py` (expose depth buffer/edge mask), `src/preview.py` (cap colouring, edges,
  callout placement, informative flag), `src/render_preview.py` (prints the flag),
  `prompts/builder.md`, `reference/scripts.md`, tests in `tests/`.
- The `run_cadquery_model.py` JSON contract keys are unchanged; the flag is printed in
  render_preview's stdout/JSON line only.
