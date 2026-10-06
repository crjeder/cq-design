## Context

Three helpers loop in Python over faces, edges or groups. `mesh_io.py` already imports `scipy.sparse.csgraph.connected_components` (line 111), so scipy is available.

## Goals / Non-Goals

**Goals:**
- Replace the per-face / per-edge loops with array operations.
- Keep results identical, including ordering.

**Non-Goals:**
- Other TODO items (1-9).
- Changing thresholds (0.9 flatness, 0.3 mm merge, 2-decimal normal rounding).

## Decisions

- `_union_find(nodes, edges)`: map node ids to 0..n-1 with a lookup array, build a COO `csr_matrix` from `edges`, call `connected_components(directed=False)`, then group nodes by label. Output groups are ordered by first appearance of each label in `nodes` and keep `nodes` order inside a group, matching the current dict-insertion order (roots are iterated in first-seen node order). Edges with an endpoint outside `nodes` do not occur at the two call sites, but ids are mapped through the lookup so a foreign id is dropped.
- `_area_cumulation_normals`: `np.unique(keys, axis=0, return_inverse=True)`, `np.add.at` for area and area-weighted normal sums. Existing ranking is a stable `sorted(..., reverse=True)` over buckets in first-seen order; use a stable sort on bucket order by first occurrence (`return_index`, reorder) so ties break identically.
- `_flat_faces`: z is already sorted. For each unused anchor `i`, group = unused entries in `[lo, hi)` from `searchsorted(z_s, z_s[i] - 0.3, 'right')` and `searchsorted(z_s, z_s[i] + 0.3, 'left')` (strict `< 0.3` on both sides). The loop remains over groups, not faces, with each step O(log n + group) instead of O(n).

## Risks / Trade-offs

- [Ordering drift changes downstream results] -> a test compares old and new implementations (kept in the test file as a reference) on a real mesh and on random inputs.
- [Float boundary at exactly 0.3 mm] -> `searchsorted` sides chosen to match strict `<`.
