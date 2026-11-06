## Context

`preview._shade_triangles` is flat Lambert; `zbuffer.rasterize` already builds a depth
buffer per pixel (SSAA) but discards it. `_cut_half` produces the kept half, so cap
triangles are exactly those coplanar with the cut plane.

## Goals / Non-Goals

**Goals:** a section of a shelf, enclosure or bracket visibly shows the cut profile; callouts only point at visible features; blank sections are detectable.

**Non-Goals:** choosing which cuts or details to render (change `preview-feature-frames`); perspective cameras; lighting models beyond cap colour and edges.

## Decisions

- **Cap colour by plane test, not by normal.** In `render_section`, mark triangles whose
  vertices all lie within 1e-3 mm of the cut position on the cut axis. They get a fixed
  cap colour; the rest keep Lambert. Colouring by normal was rejected: it is the cause of the merge.
- **Edges from the depth buffer.** Add `rasterize_with_depth` returning image and depth; an
  edge mask is pixels where depth differs from a 4-neighbour by more than a threshold
  relative to the scene depth range, plus silhouette boundary. Drawn dark, 1 px at output
  resolution. Projected B-rep edges were rejected: they need OCC edge tessellation and
  hidden-line handling, which depth edges give for free.
- **Informative flag.** Compare the cap pixel mask against the silhouette mask of the uncut
  shape in the same camera; informative iff cap area < 0.98 x silhouette area, or the cap
  has an inner hole. Returned with the path; `render_preview` prints it next to the file.
  Advisory, not a gate.
- **Callout visibility.** Project the anchor; compare its camera depth to the depth buffer at
  that pixel (tolerance ~1% of depth range); visible iff not occluded. Panel order: ortho
  panels, then iso. Merge: callouts whose chosen-panel pixel positions are within 12 px
  collapse into one badge, legend text "name xN".
- **Verbatim command.** Prompt-only change in `prompts/builder.md`; `validate_args` already
  emits the full command.

## Risks / Trade-offs

- [Depth-edge threshold misfires on thin parts] -> threshold relative to depth range; test on a thin-plate fixture.
- [Changing `rasterize` breaks callers] -> keep `rasterize` as is and add `rasterize_with_depth`.
- [Iso callouts change tile layout] -> badges go on iso only when no ortho panel sees the anchor.
