## Context

`overhang_regions` already builds a per-call `ctx` dict (edge-to-face lookup, `centroids_z`) shared by every `_is_bridge` call. The raw vertex, face and face-area arrays are still fetched via trimesh properties inside the per-region and per-edge loops. Each access verifies trimesh's cache by hashing the tracked arrays, which dominated the profile (`hash_fallback`, 302 s of 387 s).

## Goals / Non-Goals

**Goals:**
- Remove per-region and per-edge trimesh property access from `_is_bridge`.
- Keep results bit-identical.

**Non-Goals:**
- Adding `xxhash` (a separate, complementary dependency change).
- Vectorizing the per-edge loop or changing bridge logic.

## Decisions

- Store `verts`, `tris`, `area` in `ctx` at first use, as `np.asarray(...)` views. Matches the existing `centroids_z` pattern; no new signature. Alternative: add explicit parameters to `_is_bridge`; rejected as a larger diff for one internal caller.
- The arrays are read-only for the duration of the call, so a cached view is safe; the mesh is not mutated inside `overhang_regions`.

## Risks / Trade-offs

- [`ctx` initialization now holds more keys] -> populate all keys in one block alongside `lookup`.
- [`mesh.face_adjacency_edges` and `mesh.face_adjacency` still hash once per call] -> negligible, once per `overhang_regions` call.
