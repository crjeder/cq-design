## 1. Batched thickness cast

- [x] 1.1 In `src/measure_stl.py`, rewrite `_sampled_thickness` default path to one `mesh.ray.intersects_location(..., multiple_hits=True)` call, filter by facing and `t > tmin`, reduce per ray with `np.minimum.at`; keep `prefilter=False` as the reference path
- [x] 1.2 Delete the now-unused half-space prefilter loop; keep `_ray_thickness` for the reference path
- [x] 1.3 Time `_thin_regions` before/after on a ~3000-sample mesh and record the numbers in the commit message (axis-aligned 6144-face mesh, 3000 rays: 0.64s -> 0.10s; icosphere 20k faces: 5.71s -> 4.19s)

## 2. Verification

- [x] 2.1 Run `uv run pytest tests/test_thin_interfaces.py` (existing `test_prefilter_matches_unfiltered_cast` must pass unchanged)
- [x] 2.2 Run `uv run pytest tests/` and confirm no regressions
- [x] 2.3 Tick item 1 in `TODO.md` (line 87)
