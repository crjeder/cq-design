## Context

`preview.py` renders a 3x2 tile of six exterior views using OCC tessellation and matplotlib Agg. `render_preview.py` is the subprocess CLI that loads the model script and calls `render_multi_view`. `run_cadquery_model.py` invokes `render_preview.py` with `--preview` and passes along the multi-view result.

The current pipeline produces only exterior views. Hollow walls, screw bosses, cable channels, and snap hooks are invisible unless the user opens the STL in an external viewer.

## Goals / Non-Goals

**Goals:**
- Append XZ, YZ, and XY cross-section views to the multi-view tile when opt-in flag is set.
- Use existing OCC + matplotlib pipeline; no new rendering dependencies.
- Keep default behavior identical (six-view tile, no cross-sections unless `--cross-sections` is passed).

**Non-Goals:**
- Interactive cross-section planes (static centroid-plane slices only).
- Rendering the cut face as a filled polygon with a distinct material color (flat shading is sufficient).
- Per-axis enable/disable (all three planes or none).

## Decisions

### Decision: CadQuery Boolean cut for half-space, not OCC plane section

**Options considered:**
1. OCC `BRep_Algo_Section` to extract 2D wire profiles at each plane, then fill and render as flat patches.
2. `shape.cut(half_space_box)` to produce a solid half-model, then tessellate and render with the existing `_render_cq_view` pipeline.

**Choice: option 2.**

Rationale: OCC Section API produces wires that require additional triangulation and a separate 2D rendering pass - significant new code. A half-space Boolean cut produces a solid directly consumable by `_render_cq_view` with zero rendering changes. The resulting view looks like a physical cut: you see the interior geometry in 3D with the same flat shading as the rest of the model.

**Implementation:** for axis `X`, create `cq.Workplane().box(large, large, large)` translated so its right face aligns with the model's X centroid. `shape_x = shape.cut(half_box_x)`. Repeat for Y and Z.

Half-space box size: `max_extent * 4` on each side, where `max_extent = max(x_range, y_range, z_range)`. This guarantees the box always covers the full model regardless of scale.

### Decision: Camera angle per cross-section view

Each cross-section view is oriented to look into the cut face:

| Plane cut | View angle | Label |
|-----------|------------|-------|
| XZ (cut at Y centroid, keep Y- half) | Front (elev=5, azim=-90) | Section Y |
| YZ (cut at X centroid, keep X- half) | Right (elev=5, azim=0) | Section X |
| XY (cut at Z centroid, keep Z- half) | Top (elev=90, azim=-90) | Section Z |

These reuse existing view angles from `render_multi_view`, so the cross-section views are visually consistent with the exterior views.

### Decision: Extend tile layout to 3x3 when cross-sections enabled

Current tile is 3x2 (six views). Adding three cross-section views to the same 3x2 grid would replace exterior views. Instead, when `cross_sections=True`, extend to 3x3: first two rows are the existing six exterior views, third row is the three cross-section views.

The PIL compositing code in `render_multi_view` already supports variable row counts; only the `rows` constant and the `images` list need to change.

### Decision: `--cross-sections` flag forwarded through the subprocess chain

`run_cadquery_model.py` does not pass `--cross-sections` to `render_preview.py` today; it assembles the subprocess argv explicitly. Adding the forwarding is a one-line change.

## Risks / Trade-offs

- **Boolean cut failure on degenerate or manifold-error geometry** - if `shape.cut()` raises an OCC exception, the cross-section rendering falls back gracefully: the three extra views are omitted and a warning is logged to stderr. The rest of the tile renders normally.
- **Increased render time** - three additional Boolean cuts + tessellations. Estimated ~1-3 seconds per cross-section on typical parts (hollow enclosures, ~50k triangles). Acceptable for a diagnostic opt-in flag.
- **Large assemblies** - the half-space cut is applied to the compound as a whole; this is equivalent to slicing the fully assembled model, which is the desired behavior.

## Migration Plan

No data migration required. The flag is opt-in; all existing behavior is preserved when `--cross-sections` is absent.
