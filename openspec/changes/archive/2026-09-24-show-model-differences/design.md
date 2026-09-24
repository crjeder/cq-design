## Context

`interference.py` already loads trimesh + manifold3d and computes boolean volumes; `preview.py` renders headless with matplotlib Agg (CadQuery-based). STL inputs are what a delivered build or an external model provides.

## Goals / Non-Goals

**Goals:** headless, deterministic diff of two watertight STLs; JSON summary plus optional PNG.
**Non-Goals:** interactive viewing, automatic alignment (diff3d's `--align`), STEP/OBJ/3MF input, open or non-manifold meshes, gate integration.

## Decisions

- **Boolean diff, not per-triangle distance.** `only_a = A - B`, `only_b = B - A`, `common = A & B` via `trimesh.boolean` (manifold3d). Gives exact volumes and closed meshes to render. Non-watertight input fails with a clear error (loaded via `mesh_io.load_mesh`, checked with `is_watertight`). diff3d avoids booleans to support open meshes; we do not need that for printable parts.
- **No alignment.** Inputs are assumed to share a frame (both come from the same build script lineage). Misalignment shows up as a large diff, which is itself informative. Alignment is a documented follow-up.
- **Rendering:** matplotlib `Poly3DCollection` from the three result meshes, one iso view, reusing `preview._shade_triangles` for shading is avoided because importing `preview` pulls in cadquery; a small local shading is used instead. Colors: common gray, A-only red, B-only green. Empty result meshes are skipped.
- **Output contract:** JSON on stdout with `success`, `volume_a`, `volume_b`, `only_a_volume`, `only_b_volume`, `common_volume`, `bbox_delta`, `identical`, `png`, `errors`. Exit 0 on success, 1 on error.

## Risks / Trade-offs

- Boolean failure on near-degenerate meshes -> reported as an error entry, not a crash.
- Tiny numeric slivers make `identical` fragile -> use a volume tolerance (`--tol`, default 1e-3 mm^3 relative to total volume 1e-6).
