## Why

Three mesh helpers still run per-element Python loops over faces: `measure_stl._union_find`, `print_orientation._area_cumulation_normals` and `measure_stl._flat_faces`. They run on every measure and on every print-orientation search, and cost grows with face count (TODO.md item 10).

## What Changes

- `_union_find` uses `scipy.sparse.csgraph.connected_components` instead of a dict-based union-find.
- `_area_cumulation_normals` buckets rounded normals with `np.unique(..., return_inverse=True)` and sums area and area-weighted normals with `np.add.at`.
- `_flat_faces` finds each z-group by `searchsorted` on the sorted z array instead of a full-array mask per group.
- Outputs are unchanged: same components, same normals (same order), same flat-face groups.

## Capabilities

### New Capabilities

### Modified Capabilities
- `print-orientation-optimization`: adds a performance requirement; candidate normals are unchanged.

## Impact

- `src/measure_stl.py` (`_union_find`, `_flat_faces`), `src/print_orientation.py` (`_area_cumulation_normals`).
- scipy is already a dependency (used in `mesh_io.py`). No new dependencies.
