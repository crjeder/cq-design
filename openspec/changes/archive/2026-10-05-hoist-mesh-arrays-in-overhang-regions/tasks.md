## 1. Implementation

- [x] 1.1 In `_is_bridge`'s `ctx` init block (`src/mesh_io.py`), also cache `verts`, `tris`, `area` as `np.asarray(mesh.vertices / mesh.faces / mesh.area_faces)`
- [x] 1.2 Move the `ctx` init to the top of `_is_bridge`, before first use, and replace every `mesh.vertices`, `mesh.faces`, `mesh.area_faces` read in `_is_bridge` with the cached arrays

## 2. Verification

- [x] 2.1 Run `uv run pytest tests/test_mesh_io.py tests/test_sliver_fin.py` and the overhang/quality-gate tests; results must be unchanged
- [x] 2.2 Add a test counting `mesh.vertices` accesses (e.g. wrap in a subclass or monkeypatch) on a many-region mesh, asserting a constant count
