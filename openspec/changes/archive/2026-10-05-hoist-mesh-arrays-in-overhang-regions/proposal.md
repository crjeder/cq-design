## Why

Print-orientation optimization on a tray part took 387 s; 340 s was trimesh re-hashing whole mesh arrays. `_is_bridge` reads `mesh.vertices`, `mesh.faces` and `mesh.area_faces` once per overhang region and per boundary edge, and each trimesh property access runs a cache check that hashes the backing array (blake2b when `xxhash` is absent).

## What Changes

- `overhang_regions` reads `mesh.vertices`, `mesh.faces` and `mesh.area_faces` once as plain ndarrays and passes them to `_is_bridge` through the existing `ctx` dict, next to `centroids_z`.
- `_is_bridge` uses those arrays instead of `mesh.*` property access. No output change.

## Capabilities

### New Capabilities

### Modified Capabilities
- `overhang-analysis`: adds a performance requirement; detection and cost results are unchanged.

## Impact

- `src/mesh_io.py` (`overhang_regions`, `_is_bridge`). Callers (`overhang_metrics`, `support_cost`, `quality_gate`, `print_orientation`) are untouched.
- No new dependencies.
