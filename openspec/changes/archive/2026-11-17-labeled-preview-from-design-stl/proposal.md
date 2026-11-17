## Why

The current feature identification in previews is numbered badges plus a legend on the 2x2 tile. Badges merge, hide and fall back to "(not located)", and a reader has to look up each number. A hand-built reference in another project (`D:\3D Druck\Kamerahalter\preview\holder_preview_labeled.png`) works much better: the feature *names* are drawn directly on five views in per-feature colours, with a legend of what each feature is. Every project should have that image, produced by the pipeline instead of a hand-edited script with hard-coded label anchors.

## What Changes

- Add a project export step that runs the project's build script (`build/<name>.py`) and writes `preview/design.stl` in the designed pose (generalising the Kamerahalter `tools/export_design_stl.py`).
- Add a labeled-preview renderer that reads `preview/design.stl` and writes `preview/<name>_preview_labeled.png`: five views (South, above, below, isometric, West), name labels in per-feature colours with leader lines and anchor dots, a legend (name + one-line description), and a footer (bbox, triangle count, pose).
- Feature vocabulary and anchors come from the build itself: the stage labels already passed to `verify_boolean` / `verify_stage`. Each stage's geometry delta gives the anchor point; label offsets are computed (outward from the part, de-overlapped), not hand-written.
- Every project gets the labeled preview as part of the normal build/deliver flow, and it is regenerated whenever `design.stl` is older than the build script.
- Remove the numbered-badge callout overlay and its legend (`--callout`, `--unlocated-name`, badge merging, `(hidden)` entries) from the 2x2 tile. The labeled preview replaces it.
- **BREAKING**: `render_preview.py --callout` / `--unlocated-name` and the matching `run_cadquery_model.py` flags are removed; the 2x2 tile no longer carries badges or a legend row.
- Kept unchanged: feature selection (`feature_frame.py`, `--feature`, ranked `--sheet`), the engineering view (2x2 first-angle tile with compass labels), and cross-section generation (`--cross-sections`, `--extra-section`, `--auto-sections`, `--detail`).

## Capabilities

### New Capabilities
- `labeled-preview`: design-pose STL export from the build script and the five-view name-labeled reference PNG with legend, generated for every project.

### Modified Capabilities
- `preview-feature-callouts`: numbered callout badges, callout legend, hidden/merged callout handling are removed (superseded by `labeled-preview`).
- `cq-preview-rendering`: the "Callouts follow the projection" scenario is dropped from the z-buffered rasterization requirement.
- `feature-vocabulary`: ambiguous-reference echo-back refers to the label name shown in the labeled preview instead of a badge number.

## Impact

- Code: `src/render_preview.py`, `src/preview.py` (callout parsing/placement/drawing removed), `src/run_cadquery_model.py` (flag forwarding removed), `src/cq_verify.py` (opt-in stage recorder), new `src/export_design_stl.py` and `src/render_labeled.py`, build/deliver wiring in `build/build.py` template and `lib/` bundle.
- Docs: `SKILL.md`, `skill/phase3_build.md`, `skill/phase4_deliver.md`, `prompts/builder.md` (callout threading), `reference/scripts.md`, `FILES.md`, `ARCHITECTURE.md`.
- Tests: `tests/test_preview.py` callout tests replaced; new tests for the export and labeled renderer.
- Dependencies: `trimesh` and `matplotlib` are used by the reference script; the design decides whether to add them or reuse `zbuffer.py` (see design.md).
