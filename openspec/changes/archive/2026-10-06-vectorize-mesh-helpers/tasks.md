## 1. Implementation

- [x] 1.1 Rewrite `_union_find` in `src/measure_stl.py` with `connected_components`, preserving group and member order
- [x] 1.2 Rewrite `_area_cumulation_normals` in `src/print_orientation.py` with `np.unique` + `np.add.at`, preserving ranking and tie order
- [x] 1.3 Rewrite the group search in `_flat_faces` with `searchsorted` on the sorted z array

## 2. Verification

- [x] 2.1 Add tests comparing each helper to a reference copy of the old loop implementation on a CadQuery-built mesh and on random input
- [x] 2.2 Run `uv run pytest tests/` (measure, print-orientation and quality-gate tests); results must be unchanged
- [x] 2.3 Check off item 10 in TODO.md
