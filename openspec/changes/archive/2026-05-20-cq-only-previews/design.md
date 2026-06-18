## Context

`preview.py` currently renders PNG previews by loading an STL into trimesh then driving `pyrender` with an offscreen OpenGL renderer (EGL on Linux, CGL on macOS). This works on developer machines but fails in headless CI containers without a GPU or osmesa. The skill runs entirely within a CadQuery/OCC Python environment, so the geometry is already in-memory - routing through an intermediate STL file just to get a mesh for OpenGL rendering is an unnecessary round-trip.

**Current flow:**
```
model.py subprocess → exports STL → wrapper loads STL (trimesh) → pyrender (OpenGL) → PNG
```

**Target flow:**
```
render_preview.py subprocess → re-runs model.py → result (CQ Workplane) → tessellate() → matplotlib Agg → PNG
```

## Goals / Non-Goals

**Goals:**
- Remove `pyrender` (and its OpenGL requirement) from the dependency set
- Generate multi-view PNG previews using only CadQuery + matplotlib (Agg backend, no display server)
- Preserve the same external interface: `previews[]` JSON key, multi-view PNG layout
- Preserve `preview.py` public function names (`render_single`, `render_multi_view`) for any direct callers

**Non-Goals:**
- Matching pyrender's Phong-shaded appearance (matplotlib 3D is acceptable)
- Replacing trimesh for geometry validation (trimesh stays; only the render path changes)
- Supporting SVG output or changing the output format from PNG

## Decisions

### Decision 1: matplotlib Agg over CadQuery SVG export

**Alternatives considered:**
- **CadQuery SVG export** (`cq.exporters.export(..., 'output.svg')` with `projectionDir`): Generates clean technical-drawing SVGs, but converting SVG to PNG requires `cairosvg` (needs libcairo system lib) or `svglib+reportlab` (large deps). Adds a system dependency of a different kind.
- **matplotlib Poly3DCollection** (chosen): Tessellate via `result.val().tessellate()`, build face arrays, render with matplotlib `Axes3D`. Pure Python, Agg backend needs no display. `matplotlib` is a common scientific Python dependency with no system-lib requirement.
- **plotly static export**: Needs `kaleido` which bundles chromium. Heavyweight.

matplotlib wins: zero new system deps, well-known library, works headlessly out of the box.

### Decision 2: Re-run the model script in a second subprocess for preview

**Why not render in-process (wrapper process)?**
CadQuery requires Python 3.10-3.12 and a functioning OCC install. The wrapper process might not have CadQuery importable (e.g. if it was launched outside the venv). Running a dedicated subprocess guarantees the same Python executable that ran the model script is used for the preview, avoiding import-path issues.

**Why not inject preview code into the first subprocess?**
The model script runs in a temp directory with no awareness of the preview requirement. Injecting code would require wrapping every script execution, complicates the wrapper, and could interfere with the generated script's own namespace. A separate `render_preview.py` subprocess is isolated and easy to test independently.

**Why re-run the script instead of loading the exported STL?**
CadQuery cannot import STL files as solid geometry (STL is mesh-only; OCC solids are B-rep). To tessellate for rendering, we need the original CadQuery `result` object (B-rep), not the triangulated STL. Re-running the script is the only reliable way to get it without exporting STEP and paying the extra round-trip.

### Decision 3: New `src/render_preview.py` CLI, `preview.py` rewritten

`render_preview.py` is a thin subprocess entry point: accepts `--script`, `--output`, `--views`, runs the script in a local namespace, calls `preview.render_cq_multi_view(result, output)`.

`preview.py` is rewritten: `render_single(workplane, output_path, ...)` and `render_multi_view(workplane, output_path, ...)` now accept a CadQuery `Workplane` (or `Shape`). The trimesh/pyrender import chain is removed. The matplotlib 3D rendering logic lives here.

`run_cadquery_model.py` `--preview` path: instead of calling `preview.render_multi_view(tm, path)` with a trimesh object, it invokes `render_preview.py` as a subprocess.

## Risks / Trade-offs

- **Re-running the script is slower**: Preview adds roughly the same wall-clock time as the model build. This is acceptable; preview is only triggered by `--preview`, not during normal iteration.
- **matplotlib 3D depth-sorting**: `Poly3DCollection` sorts faces by centroid depth, which produces visual artifacts on complex concave models (painter's algorithm). This is a known matplotlib limitation. For most models (enclosures, brackets) the result is good enough for a preview.
- **Parametric scripts with side effects**: If a script writes files or calls external processes as a side effect, running it twice causes those side effects twice. Generated scripts are constrained to assign `result` only - this risk exists in principle but not in practice.
- **Large models**: CadQuery tessellation of very high-poly models (> 500k faces) can be slow. Configurable `tolerance` parameter on tessellate mitigates this; the renderer will use a coarser tolerance for preview.

## Migration Plan

1. Rewrite `preview.py` (new API: accepts CQ Workplane, renders via matplotlib)
2. Add `src/render_preview.py` subprocess entry point
3. Update `run_cadquery_model.py` preview section to call `render_preview.py` subprocess
4. Update `requirements.txt`: drop `pyrender`, add `matplotlib` with version pin
5. Update tests: `test_run_wrapper.py` preview mock; any direct `preview.*` call sites
6. No rollback strategy needed - change is self-contained, old pyrender path is deleted

## Open Questions

None. All decisions are resolved above.
