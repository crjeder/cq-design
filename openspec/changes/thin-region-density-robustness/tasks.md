## 1. Density-robust grouping in measure_stl

- [ ] 1.1 In `src/measure_stl._thin_regions`, split sampled faces into `thin_seed` (measured `thickness < thin_max`) and `barrier` (sampled and measured `>= thin_max`). Unsampled faces remain unknown/transparent.
- [ ] 1.2 Build connectivity over `mesh.face_adjacency` excluding any edge incident to a `barrier` face; run `_union_find` over the remaining edges to get face components (reuse the existing helper).
- [ ] 1.3 Group `thin_seed` faces by component id; keep groups with at least two seed faces (preserving the existing `< 2` noise floor, now over seeds).
- [ ] 1.4 Compute each region's stats (`thickness_mm`, `thickness_mean_mm`, `thin_direction`, orientation, centroid, `brittle`, `nearest_feature`) from the group's seed faces only -- never from transparent unsampled faces. Keep all current output fields.
- [ ] 1.5 Confirm the path is a no-op at or below the cap: when every face is sampled, barrier-flood grouping reduces to today's thin-thin adjacency grouping.

## 2. Tests

- [ ] 2.1 `tests/test_thin_interfaces.py` (or `test_mesh_io.py`): a thin-in-XY wall fixture at a coarse tessellation (<= cap) reports the region; the same wall subdivided past `max_samples` still reports it -- the regression guard for the fragmentation bug.
- [ ] 2.2 Result-stability assertion: coarse and fine measurements of the same wall report comparable `thickness_mm`.
- [ ] 2.3 A uniformly thick mesh above the cap reports no regions (no spurious regions from the transparent unsampled faces).
- [ ] 2.4 (Fast variant) exercise the high-stride path by passing a small `max_samples` so the test does not need a huge mesh.

## 3. Verification

- [ ] 3.1 `uv run pytest tests/test_thin_interfaces.py tests/test_mesh_io.py` pass.
- [ ] 3.2 `ruff check` / `ruff format` clean on changed files; mypy and basedpyright clean on `src/measure_stl.py`.
- [ ] 3.3 Remove the resolved "thin-wall detection silently weakens above 3000 faces" line from `TODO.md`; update the `measure_stl.py` description in `CLAUDE.md` if the grouping note warrants it.
