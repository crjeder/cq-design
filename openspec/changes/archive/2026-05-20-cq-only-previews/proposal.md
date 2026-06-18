## Why

`preview.py` renders previews via `pyrender`, which requires an OpenGL context (EGL on headless Linux, osmesa as CPU fallback). This creates a fragile system-level dependency that breaks in CI and containerised environments. Since the skill is already running CadQuery, we have direct access to OCC geometry and can render without any graphics driver.

## What Changes

- **`src/preview.py`** rewritten: replaces `pyrender` + trimesh-based rendering with CadQuery tessellation (`result.val().tessellate()`) + matplotlib (`Agg` backend, no OpenGL required)
- **`src/render_preview.py`** added: thin CLI wrapper that re-runs a model script in a CadQuery environment, captures the `result` workplane, and calls the new preview renderer
- **`src/run_cadquery_model.py`** updated: `--preview` mode invokes `render_preview.py` as a subprocess instead of calling `preview.py` in-process against an STL-derived trimesh
- **`requirements.txt`** updated: drops `pyrender`, adds `matplotlib` (if not already present)

## Capabilities

### New Capabilities

None. Preview output contract (PNG path in `previews[]` JSON key, multi-view layout) is unchanged.

### Modified Capabilities

None. The `preview-and-validate` spec governs the wrapper JSON contract only, not how the PNG is rendered. No requirement changes.

## Impact

- `pyrender` removed from `requirements.txt` and from the runtime path
- `preview.py` public API (`render_single`, `render_multi_view`) is preserved but signatures change: accepts a CadQuery `Workplane` instead of a `trimesh.Trimesh`
- `run_cadquery_model.py` preview path changes: model script is re-executed in a second subprocess to obtain the live `result` CQ object; STL is still used for geometry validation only
- Any direct callers of `preview.render_single` / `preview.render_multi_view` must pass a CadQuery `Workplane`, not a mesh
- Rendering style changes: matplotlib `Poly3DCollection` output vs. pyrender Phong-shaded; different visual appearance, same information content
