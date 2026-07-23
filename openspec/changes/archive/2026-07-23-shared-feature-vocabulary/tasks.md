# Tasks: shared-feature-vocabulary

## 1. Compass panel labels

- [x] 1.1 Build a small asymmetric CadQuery fixture with a distinguishable marker on
      its North (+Y) face; render the multi-view tile and record which panel shows
      the marker, fixing the camera-to-compass mapping empirically (design D5)
- [x] 1.2 Rename the three ortho panel labels in `preview.py` `render_multi_view` to
      the verified compass viewing-station names; update the docstring's panel table
- [x] 1.3 Update `tests/test_preview.py` label assertions; add a fixture-based test
      that the North-station panel shows the North-face marker and no label contains
      "Front"/"Left"/"left"/"right"

## 2. Callout overlay in the renderer

- [x] 2.1 Add `--callout "name=<n>;center=x,y,z"` parsing to `render_preview.py`
      (reuse the `--detail` spec-parsing conventions; malformed spec exits non-zero
      naming the spec)
- [x] 2.2 In `preview.py`, project each callout center through the live `Axes3D`
      (`proj3d.proj_transform` + data transform) and draw numbered badges with leader
      lines on the three ortho panels only, before rasterization (design D2)
- [x] 2.3 Render the legend row in the caption area: badged names in supply order,
      then unlocated names marked "(not located)"; no legend when no callouts
- [x] 2.4 Thread callout specs through `run_cadquery_model.py` alongside
      `extra_sections` (build_preview_cmd + CLI flag pass-through)
- [x] 2.5 Tests: badges present in ortho panels and absent from isometric; unchanged
      tile without callouts; malformed spec diagnostic; legend text matches supplied
      names verbatim

## 3. User-noun naming rule

- [x] 3.1 Add the naming rule to `prompts/planning.md`: user nouns verbatim
      (mechanical normalization only), coined names only for unnamed things,
      collision suffix surfaced in the summary
- [x] 3.2 Update `skill/phase2_planning.md` plan-summary checkpoint: introduce every
      coined name explicitly; interfaces table shows agreed names

## 4. Conversational vocabulary rules

- [x] 4.1 Add the compass-only prose rule to `skill/phase2_planning.md` and
      `skill/phase3_build.md` (left/right/front/back only when quoting the user)
- [x] 4.2 Add the echo-back rule to `skill/phase3_build.md` checkpoint prose: restate
      spatial/unagreed references as `name (badge)`; confirm when ambiguous
- [x] 4.3 Update `skill/phase3_build.md` step 4 preview invocation to thread one
      `--callout` per interface with `name` + `position_mm` (plan order), and list
      remaining named interfaces for the legend

## 5. Documentation and verification

- [x] 5.1 Update USE.md and CLAUDE.md script-table rows to mention callouts and the
      compass panel labels; reconcile USE.md's viewer convention with the verified
      panel mapping from 1.1
- [x] 5.2 Run the fast test subset plus `tests/test_preview.py`; render one
      real-plan part preview with callouts end-to-end via
      `run_cadquery_model.py --preview` and eyeball the tile
