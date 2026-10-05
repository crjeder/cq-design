## 1. Implementation

- [x] 1.1 In `_thin_regions`, precompute `mesh.face_normals` and compute the facing mask `N @ D.T > eps` for the sampled rays (chunk if large)
- [x] 1.2 Add the in-front half-space filter and run `_ray_thickness` only on each ray's surviving triangle subset
- [x] 1.3 Keep the `inf` result when the subset is empty; leave region grouping untouched

## 2. Verification

- [x] 2.1 Add a test in `tests/test_thin_interfaces.py` asserting filtered thickness equals the unfiltered cast on a watertight fixture
- [x] 2.2 Run `uv run pytest tests/test_thin_interfaces.py` and confirm unchanged region output
- [x] 2.3 Time a dense fixture before and after; drop the change if it is not faster
