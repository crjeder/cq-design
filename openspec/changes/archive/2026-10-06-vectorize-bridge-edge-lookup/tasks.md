## 1. Edge lookup in mesh_io

- [x] 1.1 Time the `ctx["lookup"]` build versus the per-region loop on a many-region mesh (or the tray mesh) to confirm where `_is_bridge`'s own time goes; note the split in the PR
- [x] 1.2 Replace the `lookup` dict with int64 sorted edge keys plus pair array, built vectorized in `overhang_regions` and passed through `ctx`
- [x] 1.3 Vectorize the boundary-edge loop in `_is_bridge` (searchsorted lookup, in-region and rising-lip masks, one `to_rect` product, `bincount` per side)
- [x] 1.4 Add a test comparing bridge flags and `support_cost` against the old per-edge implementation on the existing bridge fixtures and a many-region mesh

## 2. Shared data in print_orientation

- [x] 2.1 Compute `base.area_faces` before the candidate loop and set it in each posed copy's cache after `apply_transform`; test equality with a fresh `posed.area_faces`
- [x] 2.2 Compute `bed_contact_mask` once per pose and pass it to `_support_metrics`, `_gentle_incline_fraction` and `_stability_metrics`
- [x] 2.3 Test that `optimize_orientation` scores and chosen orientation are unchanged and that the mask is evaluated once per pose

## 3. Verification

- [x] 3.1 Run the full suite (`uv run pytest tests/`) and ruff, mypy, basedpyright on changed files
- [ ] 3.2 Re-profile the tray run (`python -m cProfile -s cumtime build/build.py`) after updating its `lib/`, and record before/after in the PR
