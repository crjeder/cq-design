## 1. Stage recorder and STL export

- [x] 1.1 Add opt-in stage recorder to `src/cq_verify.py` (module-level start/stop gate; stores label, operation, delta bbox/centroid/volume, never the shapes); test that it is a no-op when disabled
- [x] 1.2 Write `src/export_design_stl.py` (run build script, tessellate 0.05/0.1, compound for dict results, write `design.stl` + `design.features.json`, JSON contract and exit codes)
- [x] 1.3 Tests: export on a two-stage fixture script, missing-`result` failure, dict result

## 2. Labeled renderer

- [x] 2.1 Write `src/render_labeled.py`: load STL, five fixed orthographic views via `zbuffer.make_camera`, shading and edge lines, compass panel titles
- [x] 2.2 Anchor selection from delta bbox/centroid with per-view z-buffer visibility; `(hidden)` handling
- [x] 2.3 Deterministic label placement (outward offset, greedy de-overlap, stay inside panel) and fixed 12-colour palette
- [x] 2.4 Legend (plan description, else operation + delta size), footer (bbox, triangles, pose), `no named features` case
- [x] 2.5 Tests: five panels present, label overlap check, determinism (byte-identical), hidden feature, no OpenGL import, 11-feature fixture modelled on the Kamerahalter holder

## 3. Wiring into build and deliver

- [x] 3.1 Call export + render from `build/build.py` (template and `lib/` bundle) with the freshness skip
- [x] 3.2 Bundle `export_design_stl.py` and `render_labeled.py` into `lib/` and list them in the bundle manifest
- [x] 3.3 Update `skill/phase3_build.md` / `skill/phase4_deliver.md` to show and cite the labeled preview, with names in prose per `feature-vocabulary`

## 4. Remove the callout path

- [x] 4.1 Delete `--callout` / `--unlocated-name` parsing and forwarding in `src/render_preview.py` and `src/run_cadquery_model.py`
- [x] 4.2 Delete `_place_callouts`, `_draw_callouts`, badge merging and the legend line from `src/preview.py`; keep the marker drawing used by `--feature` views
- [x] 4.3 Remove callout threading from `prompts/builder.md`, `SKILL.md` and the phase docs; add a test that no `--callout` string remains in `prompts/`, `skill/`, `SKILL.md`
- [x] 4.4 Replace callout tests in `tests/test_preview.py`; confirm 2x2 tile, `--cross-sections`, `--feature` and `--sheet` tests pass unchanged

## 5. Docs and verification

- [x] 5.1 Update `reference/scripts.md`, `FILES.md`, `ARCHITECTURE.md` and the `CLAUDE.md` script index for the two new scripts and removed flags
- [x] 5.2 Run the full suite (`uv run pytest tests/`) and `ruff check` / `ruff format` on changed files
- [x] 5.3 Render the labeled preview for the Kamerahalter holder and compare with `holder_preview_labeled.png` (all 11 names present, no overlaps)
