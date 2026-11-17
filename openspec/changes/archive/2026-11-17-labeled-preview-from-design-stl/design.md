## Context

Reference implementation: `D:\3D Druck\Kamerahalter\tools\export_design_stl.py` (runs `build/holder.py`, exports `preview/design.stl` at tolerance 0.05 / angular 0.1) and `tools/render_labeled.py` (trimesh + matplotlib `PolyCollection`, painter's-algorithm face sorting, five views). Its weaknesses: the colour map `C`, the label table `L` (anchor + offset per view) and the legend rows `ROWS` are hand-written per project, and the file name and title are hard-coded to "holder".

In this repo, the 2x2 tile (`preview.render_multi_view`) is rendered from live CadQuery geometry with `zbuffer.py`, and features are marked with numbered badges (`_place_callouts`, `_draw_callouts`) fed by `--callout` specs threaded from `BUILD_PLAN.json` interfaces. Named features already exist in build scripts as the stage labels passed to `cq_verify.verify_boolean` / `verify_stage`.

## Goals / Non-Goals

**Goals:**
- Every project produces `preview/design.stl` and `preview/<name>_preview_labeled.png` with no per-project hand-editing.
- Labels show feature names directly; legend gives name + description.
- Callout badges and their legend machinery are deleted, not left as a second path.

**Non-Goals:**
- No change to the engineering view tile, cross-section generation, `feature_frame.py`, `--feature`, or the ranked `--sheet`.
- No change to the delivered STL/3MF/STEP (`design.stl` is a preview artifact in the designed pose, never delivered).
- No interactive or 3D viewer output.

## Decisions

**1. Two scripts under `src/`, bundled to `lib/`:** `export_design_stl.py <build_script> [out.stl]` and `render_labeled.py <stl> <features.json> [out.png]`. Tessellation tolerances copied from the reference (0.05 / 0.1). Rationale: deterministic file I/O and geometry belong in `src/` with a JSON contract and a test (CLAUDE.md program-vs-prompt rule). Alternative considered: one combined script; rejected because the STL is also useful on its own (diffing, external viewers) and the reference already splits them.

**2. Feature vocabulary = stage labels recorded during the build.** `cq_verify` gets an opt-in recorder (a module-level start/stop gate switched on only by the export script) that appends `(label, before, after)` per `verify_boolean`/`verify_stage` call. The export script writes `preview/design.features.json` with, per label, the delta solid's bbox and centroid and the stage operation (union/cut/fillet). Alternatives: (a) only `BUILD_PLAN.json` interfaces with `position_mm` - kept as a secondary source because they carry descriptions, but many features (fillets, notches, pegs) have no interface; (b) parse the build script text for labels - fragile. Without the recorder, behaviour of `cq_verify` is unchanged.

**3. Anchors are computed, not authored.** For each feature, collect mesh triangles whose centroid lies within the delta bbox (grown by a small epsilon), and for each view pick the visible one (z-buffer test, reusing `zbuffer.py`) closest to the delta centroid. The feature is labeled in each view where it is visible; a feature visible in no view is listed in the legend as `(hidden)`. Rationale: removes the `L` table; reuses the visibility test the callouts already had. Alternative: keep authored anchors in a sidecar file; rejected as it recreates the manual step.

**4. Label placement:** offset outward from the part silhouette along the dominant free direction, then a greedy pass shifts labels vertically/horizontally until no two label boxes overlap and none crosses the axes frame. Placement is deterministic (features processed in vocabulary order). Alternative: matplotlib `adjustText`; rejected as a new dependency.

**5. Rendering with `zbuffer.py` + Pillow, not matplotlib painter's sort.** The reference's per-triangle sorting shows seams and ordering artefacts, and matplotlib/trimesh are not project dependencies. The existing numpy rasterizer gives per-pixel depth and edge lines, and the same camera helper (`zbuffer.make_camera`) already handles orthographic bases. The five views are fixed: South, above, below (Y flipped), isometric, West. Colours come from a fixed 12-colour categorical palette assigned in vocabulary order, wrapping after 12. Alternative: add trimesh + matplotlib as dev-group deps and port the script verbatim; rejected to keep the headless, no-new-dependency property in `cq-preview-rendering`.

**6. Wiring:** `build/build.py` (template and `lib/` bundle) runs export then render after the model builds, skipping both when `preview/design.stl` is newer than the build script (the existing freshness check in `freshness.py`). The legend description comes from the matching `interfaces[].description` when a name matches, otherwise the operation (`union`/`cut`/`fillet`) and delta bbox size. File name is `<script_stem>_preview_labeled.png`. Multi-union (dict) results export one compound.

**7. Remove, do not deprecate, the callout path.** `--callout`, `--unlocated-name`, `_parse_callout_spec`, `_place_callouts`, `_draw_callouts`, badge merging and the legend line are deleted along with their forwarding in `run_cadquery_model.py` and the threading text in `prompts/builder.md` and the phase docs. `feature-vocabulary` echo-back now cites the label name.

## Risks / Trade-offs

- [Delta solid of a fillet or a cut is thin or fragmented, anchor lands off-feature] -> use the largest-volume solid of the delta; if the delta is empty fall back to the stage bbox centre and mark nothing as hidden.
- [Label placement overlaps on dense parts] -> greedy relocation plus a cap of one label per feature per view; overflow features go to the legend only. Test with the Kamerahalter part as the golden fixture (11 features).
- [Recorder holds `before`/`after` shapes in memory for large models] -> store only bbox, centroid and delta volume at record time, not the shapes (delta computed once, then dropped).
- [Removing callout flags breaks existing builder prompts] -> grep all prompts/commands in the same change; add a test that no `--callout` string remains in `prompts/`, `skill/`, `SKILL.md`.
- [Projects with no stage labels get an empty vocabulary] -> the image still renders (views + footer) and the legend states "no named features"; `BUILD_PLAN.json` interfaces with `position_mm` are used as the fallback vocabulary.

## Migration Plan

1. Land the new scripts and recorder alongside the old callout path, with tests.
2. Switch `build/build.py` and docs to the labeled preview, delete the callout path in the same change.
3. `/cq-design:update` re-copies `lib/` and `build/build.py` into existing projects; the next build regenerates the labeled preview. Rollback: revert the change; no data migration (previews are regenerable).

## Open Questions

- Interpretation check: "replaces the current preview generation" is read as replacing the numbered-callout labeling of features, while the 2x2 engineering tile, cross sections and the feature selection/sheet stay. If the intent is also to drop the per-feature close-up sheet, say so and `feature-preview-frames` gets a removal delta.
- Should `design.stl` and `*.features.json` be committed in the project, or ignored like `build/` temp files? Default here: kept in `preview/`, not bundled into deliverables.
