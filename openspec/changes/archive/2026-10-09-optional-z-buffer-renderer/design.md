## Context

`_render_cq_view` built a `Poly3DCollection` and let mplot3d sort triangles by mean depth. The TODO suggested trimesh + pyrender, but `cq-preview-rendering` guarantees no OpenGL/EGL/osmesa/display, and the archived `2026-05-20-cq-only-previews` change removed that stack deliberately.

## Goals / Non-Goals

**Goals:** correct per-pixel occlusion, headless, no new dependency, same look (light, base color, background) and same compass-station camera convention.

**Non-Goals:** smooth shading, shadows, perspective, textures, an opt-in/legacy matplotlib mode.

## Decisions

1. **Numpy rasterizer over pyrender.** Pyrender needs a GL context. The rasterizer loops per triangle and vectorizes per pixel (barycentric mask + depth compare). Alternative considered: fully vectorized splatting - rejected, higher memory, no clear win.
2. **2x supersampling, box downsample** for edge quality (no other antialiasing).
3. **Camera matches matplotlib's `view_init(elev, azim)` convention** so the compass-labelled panels keep their meaning (verified by the existing north-marker test). All views orthographic.
4. **Framing:** whole-part views fit the projected bbox to 90% of the canvas; focus (detail) views use the same `0.6 * size` half-window as before.
5. **Callouts** are drawn with PIL after rasterizing, projected through the same camera function.
6. **Replace, not option:** user decision; keeps one code path.
7. `_shade_triangles` vectorized with `np.cross` (returns an (n, 3) array).

## Risks / Trade-offs

- [Slower on very dense meshes] -> per-triangle bbox loop; acceptable at preview tolerance (0.05).
- [Hairline seam artifacts at shared edges] -> edge test is inclusive (`>= 0`); observed only as isolated sub-pixel specks.
- [Iso panel no longer perspective] -> accepted; documented.
