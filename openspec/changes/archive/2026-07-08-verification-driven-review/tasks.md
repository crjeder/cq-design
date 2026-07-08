## 1. Deterministic disconnected-body check

- [x] 1.1 In `src/run_cadquery_model.py`, after each union body is tessellated, split
      it into connected components (trimesh body count) and, when a union yields more
      than one component, append an `errors` entry with `type: "disconnected_body"`,
      `union` id, `component_count`, each component's bbox + volume in `message`, and a
      hint to union/bridge the pieces. Treat it as blocking (like `non_watertight`).
- [x] 1.2 Exclude keep-out zones; run the check per declared union (single-`Workplane`
      result = one union id = part id; `dict` result = one check per union key).
      (Keep-out zones never reach the per-union STL loop: `run_model_shim` already
      skips `KEEP_OUT_KEY` on export, so the check only ever sees real union bodies.)
- [x] 1.3 In `tests/test_run_wrapper.py`, add a fixture whose `result` is two
      non-overlapping boxes added into one body and assert exactly one
      `disconnected_body` error with `component_count: 2`; assert a normal single-body
      part reports none.

## 2. Default preview tile: 2x2 first-angle DIN, true orthographic

- [x] 2.1 In `src/preview.py`, redefine `render_multi_view`'s default from the six-view
      3x2 tile to a 2x2: Front (look -Y) top-left, Left side (view-from-left, camera on
      -X looking +X) top-right, Top (look -Z) bottom-left, Isometric bottom-right.
- [x] 2.2 Set `ax.set_proj_type("ortho")` and exact axis-aligned angles (elev 0 for
      Front/Left, elev 90 for Top; no 5-degree tilt) for the three ortho panels; leave
      the isometric panel pictorial.
- [x] 2.3 Keep the caption/footer showing overall bbox W x D x H, volume, triangles,
      PLA estimate; draw no dimension lines on the panels.
- [x] 2.4 Label each panel with its view name (Front / Left / Top / Isometric).
- [x] 2.5 In `tests/test_preview.py`, update the six-view assertions to the 2x2 layout
      and assert the ortho panels are produced (no import of pyrender/OpenGL, unchanged).

## 3. Cross-sections as separate files through declared positions

- [x] 3.1 Change `--cross-sections` so it no longer appends a section row to the tile;
      instead write one section PNG per cut as a separate file (reuse the existing
      section-file naming), returned in `previews[1:]`.
- [x] 3.2 Cut each section through a declared feature/union position supplied by the
      caller (from `BUILD_PLAN.json` interfaces/unions), falling back to the
      bounding-box center cuts when no positions are supplied.
- [x] 3.3 Thread the declared positions from `run_cadquery_model.py` into
      `render_preview.py`. Repurposed the existing `--extra-section` list as the
      caller-supplied position channel (the wrapper already forwards it); SKILL.md
      Step 3 instructs Claude to pass declared feature/union positions there.
- [x] 3.4 Update `tests/test_preview.py` / `test_run_wrapper.py` for separate section
      files (count + naming), replacing the nine-view-tile assertions.

## 4. Question-driven review workflow

- [x] 4.1 Rewrite `reference/Visual Review Checklist.md` as a question bank: a fixed
      universal-invariant set (single connected body / no floating solids; flat face at
      Z=0; proportions; shape match; authored orientation) plus a per-feature question
      template (one question per interface, block, and union), each tagged with the view
      that answers it and requiring the answer to cite that view.
- [x] 4.2 In `SKILL.md` Step 4, replace the open-ended "inspect the tile against 10
      items" flow with: generate the question list from the part's `BUILD_PLAN.json`
      entry + universal invariants; answer each against a cited view; render the needed
      section/detail first when no view shows the geometry; any "no" is a
      `visual_mismatch` naming the question, using the existing retry budget.
- [x] 4.3 In `SKILL.md` Step 3, update the render invocation: 2x2 default tile, and
      `--cross-sections` (separate files) driven through declared feature/union
      positions so interior questions have a crossing view.
- [x] 4.4 State in `SKILL.md` that review-input artifacts (the tile + its section files
      for the attempt under review) SHALL be read before any re-render can overwrite
      them; render to stable per-part names. (Also updated `CadQuery Pattern
      Reference.md` gotcha 12 to point at the question bank instead of the old item 8.)
- [x] 4.5 Update the SKILL error-handling reference so `visual_mismatch` reflects the
      question-driven form (names the failed question + cited view) and add
      `disconnected_body` to the wrapper error table.

## 5. Verify

- [x] 5.1 `uv run pytest tests/test_run_wrapper.py tests/test_preview.py`
- [x] 5.2 `openspec validate verification-driven-review --strict`
- [x] 5.3 Regenerate the cradle part (or an equivalent disconnected-body fixture) and
      confirm `disconnected_body` fires and the connectedness question fails against the
      junction section file. (Confirmed: a foot+neck+ring cradle reports
      `disconnected_body` union=cradle component_count=3, and `--cross-sections` writes
      the separate section files the connectedness question is answered against.)
