## Why

A part that had to be one connected body shipped as three detached solids (a foot
bar, a diagonal neck, and a free-floating ring). The part loop's visual self-review
did not catch it. The post-mortem shows three compounding failures, not one:

1. **Coverage.** The disconnection was only visible in a cross-section that crossed
   the foot/neck junction. Exterior and isometric views overlap in projection and
   read as touching, so the default center cuts (and every exterior panel) missed it.
2. **Forcing function.** The one image that did reveal the gap was a `--detail`
   section file, but Step 4 graded against the overview tile and self-certified. The
   review is an open-ended "inspect the render against a 10-item checklist" -- nothing
   forces the reviewer to look at the specific view that shows a specific feature.
3. **Artifact lifecycle.** The overview render was overwritten before the review read
   it, so the review ran against a stale/absent image.

Connectedness in particular did not need vision at all: a union that tessellates into
more than one component is a deterministic geometry fact the wrapper can assert.

## What Changes

- **Add a deterministic disconnected-body check.** `run_cadquery_model.py` counts
  connected components per union body; a union expected to be one solid that splits
  into more than one emits a blocking `disconnected_body` error. This catches the
  cradle bug cold, independent of the render. (Capability: `structured-errors`.)
- **Make the visual review question-driven (CADCodeVerify pattern).** Replace the
  open-ended checklist pass with a generated question set: one yes/no question per
  planned interface, block, and union from `BUILD_PLAN.json`, plus a fixed set of
  universal invariants (single connected body, flat bed face at Z=0, proportions,
  shape match, authored orientation). Each question is answered against a **named
  view**, and the answer must cite which view it was judged from. A question whose
  geometry no rendered view actually shows triggers rendering that view first; any
  "no" is a `visual_mismatch` naming the question. (Capability: `visual-self-review`.)
- **Guarantee section coverage through declared positions.** `--cross-sections`
  stops appending to the tile and instead writes **separate section files, on
  request**, cut through each declared feature/union position (not only the
  bounding-box center), so the connectedness and internal-feature questions have a
  view that actually crosses the geometry. (Capability: `preview-cross-sections`.)
- **Redesign the default preview tile.** The default multi-view render becomes a 2x2
  first-angle (DIN) projection: Front (Vorderansicht) top-left, Left side
  (Seitenansicht, view-from-left drawn on the right) top-right, Top (Draufsicht)
  below the front, and an isometric view in the free corner. The three orthographic
  panels use true orthographic projection (no perspective tilt); overall bounding-box
  dimensions stay in the caption only (not drawn on the views). Fewer, larger,
  undistorted panels give a vision reviewer better signal than a nine-up contact
  sheet. (Capability: `cq-preview-rendering`.)
- **Protect review artifacts.** The exact files a review depends on SHALL NOT be
  overwritten before the review reads them. (Capability: `visual-self-review`.)
- **Adapt the review workflow.** `SKILL.md` Step 4 and `reference/Visual Review
  Checklist.md` are rewritten from "inspect the 3x3 tile against 10 items" to
  "generate questions from the plan + universal invariants, answer each against a
  cited view, connectedness answered against section files."

## Capabilities

### Modified Capabilities
- `structured-errors`: add a `disconnected_body` typed error for a union body that
  tessellates into more than one connected component.
- `visual-self-review`: the review is question-driven -- questions generated from the
  plan plus universal invariants, each answered against a cited view; connectedness
  is a mandatory invariant answered against section files; review-input artifacts are
  not overwritten before they are read.
- `cq-preview-rendering`: the default multi-view tile is a 2x2 first-angle DIN
  projection (Front / Left-side-on-right / Top / Isometric) using true orthographic
  projection for the three ortho panels, with overall bbox dimensions in the caption.
- `preview-cross-sections`: `--cross-sections` writes separate section files on
  request, cut through declared feature/union positions, instead of appending a
  section row to the tile.

## Impact

- Code: `src/run_cadquery_model.py` (per-union component-count check ->
  `disconnected_body`), `src/preview.py` (`render_multi_view` 2x2 first-angle layout +
  ortho projection; sections to separate files), `src/render_preview.py` /
  `run_cadquery_model.py` (`--cross-sections` semantics: separate files through
  declared positions).
- Docs/workflow: `SKILL.md` (Step 3 render invocation, Step 4 question-driven review),
  `reference/Visual Review Checklist.md` (rewritten as a question bank).
- Tests: `tests/test_run_wrapper.py` (disconnected_body), `tests/test_preview.py`
  (2x2 layout, ortho panels, separate section files).
- The `disconnected_body` check is independent and could ship alone; the render +
  review changes are coupled (the questions are answered against the redesigned views).
