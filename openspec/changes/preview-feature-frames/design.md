## Context

Interfaces carry `name`, `position_mm`, `wall`, and 2D `diameter_mm` / `size_mm`; no depth or
normal. `render_prompt.section_cuts` already ranks interfaces by `request_log` kind
(clarification > correction > rest) and caps at `MAX_SECTIONS = 3`. `section_select`
detects axis-aligned cylinders only. `preview.render_detail_view` has a fixed camera and no
marker. Builds on `preview-section-readability` (cap colour, edges, z-buffer visibility).

## Goals / Non-Goals

**Goals:** every relevant named feature gets a view in which it is visible and marked, with a section where it has depth; whole parts get meaningful cuts; output stays within one 2 x 2 sheet.

**Non-Goals:** schema changes (depth is solid-derived); perspective cameras; non-axis-aligned section planes (the plane is axis-aligned after snapping the normal to the nearest world axis; oblique features fall back to a detail view without section).

## Decisions

- **Feature frame from the solid.** Faces of the built solid whose bbox intersects a window
  of radius `max(diameter_mm, max(size_mm), 2)` around `position_mm`, excluding faces that
  span more than 2x the window (the host wall). Frame = union bbox of the remaining faces,
  normal = area-weighted dominant face normal snapped to a world axis, depth = bbox extent
  along that normal. No faces found -> frame is None -> feature stays "not located".
  Alternative (add bbox/depth to schema) rejected: the planner would have to guess.
- **Camera and section.** Camera = along the normal toward the viewer (flipped if the
  anchor fails the visibility test, then iso fallback). Section plane contains the normal
  and the feature's longer in-plane axis, positioned at the bbox centre; emitted only if
  depth >= 0.5 mm (has depth). Marker = the readability change's badge drawn at the projected
  anchor in every feature view.
- **Whole-part sections by slice analysis.** Sample 15 planes per axis through the bbox
  (OCC section of the solid). Score = inner-loop count x 1.0 + void area fraction x 2.0 +
  normalised area change vs neighbours. Take top candidate per axis, drop any within 0.5 mm of a
  feature cut or reserved cut, keep best 2 overall. `section_select` bore cuts remain and take
  precedence when they show more features.
- **Relevance ranking.** Score per feature: explicit mention in the current user prompt
  (name match in request text) > targeted by request_log `correction` or `clarification` /
  ask_user answer > other request_log mention > declared interface order by size. Whole-part
  sections fill remaining slots after features. Total sheet cap 4: tiles = ranked features
  then sections until 4 are used. If no feature qualifies, the sheet is 4 whole-part tiles
  (or fewer). Ranking is deterministic code in `render_prompt.py`, reusing the existing
  request_log ranking helper; the model decides nothing.
- **2 x 2 sheet.** `preview.render_sheet(tiles, path)` composes up to 4 tile images with
  captions (name, view kind) into one PNG; each tile also written full-size as today. Sheet
  is the file the reviewer opens first; the others are for drill-down.
- **CLI.** `render_preview.py --feature "name;center=x,y,z;diameter=d|size=w,h" ...` and
  `--sheet`; `validate_args` emits them from the plan and ranking. `--detail` and
  `--extra-section` remain for manual use.

## Risks / Trade-offs

- [Window picks wrong faces on dense parts] -> exclude host-wall faces; test on boss-on-plate, hole-in-wall and slot fixtures; fall back to "not located".
- [Normal snapped to axis misframes angled features] -> detail view without section, noted in the legend.
- [Slice scoring costs time on complex parts] -> 15 slices x 3 axes with early exit past 5 s, then fall back to bbox-centre cuts.
- [Cap of 4 hides a relevant feature] -> unselected features listed in the legend as "(not shown)" with the `--feature` flag to render them on demand.

- **Re-rank every build.** The sheet is re-ranked on each validate run, not pinned to the
  first selection. Features changed since the previous build (script diff / request_log
  entries newer than the last build) rank above unchanged ones within the same relevance
  tier, so the sheet follows the work in progress.
