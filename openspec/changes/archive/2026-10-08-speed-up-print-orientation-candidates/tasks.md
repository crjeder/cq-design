## 1. Baseline

- [x] 1.1 Add a parity test capturing per-candidate scores, chosen orientation and per-region bridge flags from the current code on a mesh with many small overhang regions
- [x] 1.2 Histogram region face counts and line-profile one candidate to confirm where `_is_bridge` time goes

## 2. Shared per-mesh data

- [x] 2.1 Compute base centroids once in `optimize_orientation`; pass per-pose `centroids_z = centroids @ R[2] + tz` to `bed_contact_mask` and `_is_bridge` (optional args, default to current behavior)
- [x] 2.2 Build adjacency `keys`/`pairs` once per base mesh and pre-seed `ctx` for the `overhang_regions` call made by `support_cost`

## 3. `_is_bridge` cost

- [x] 3.1 Bulk-gate regions with `bincount` over component labels in `overhang_regions`; loop only over survivors
- [x] 3.2 Replace `np.unique(edges, axis=0)` with 1-D edge keys
- [x] 3.3 Skipped: 1.2 shows only the ~7% of regions passing the gate reach qhull, so no tiny-region fast path

## 4. Verify

- [x] 4.1 Run `uv run pytest tests/test_mesh_io.py tests/test_sliver_fin.py` plus the print-orientation tests and the parity test
- [x] 4.2 Re-timed on a synthetic 60-candidate mesh only (0.54 s -> 0.37 s, identical output); the 205-candidate real part was not available to re-time. TODO.md item 5 marked done, (c) pruning deferred
