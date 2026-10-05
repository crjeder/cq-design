## 1. Metric

- [x] 1.1 Add `fold_metrics(mesh, min_interior_deg)` and a `FOLD_MIN_INTERIOR_DEG = 10.0` constant to `src/mesh_io.py` (trimesh `face_adjacency`/`face_adjacency_angles`, union-find clustering on shared vertices)
- [x] 1.2 Unit tests in `tests/test_mesh_io.py` on hand-built meshes: opposite-normal triangle pair (fin), box, cylinder, 20 degree wedge tip, multi-pair fin clusters to one

## 2. Gate

- [x] 2.1 In `quality_gate._analyze_stl`, after the watertight check, call `fold_metrics` and emit `sliver_fin` (`warning`, up to 5 locations, build frame, hint per spec)
- [x] 2.2 Tests in `tests/test_quality_gate.py`: fin mesh emits the issue; clean mesh emits nothing; rotated pose reports build-frame location

## 3. Validation

- [x] 3.1 Run `fold_metrics` over `evals/cases/*/golden/*.stl` and `tests/fixtures`; record the sharpest interior angle per part. Confirm none is below 10 degrees (adjust threshold or add an exclusion note if any is)
- [x] 3.2 Add the reproducer as a CadQuery fixture (`tests/fixtures/rim_fillet_fins.py.txt`) and `tests/test_sliver_fin.py`: four fins in the original, none once the prism ends on the rib flank (`1 - 2 * f / RIB_DEPTH`). Overlapping the prism into the torus was tried and does not remove them
- [x] 3.3 Open questions in design.md resolved: stays `warning` (the reproducer's sharpest fold is 1.4 degrees at export tolerance, so a sub-1 degree error tier would miss it); per-part gate only

## 4. Docs

- [x] 4.1 `reference/scripts.md`: add `sliver_fin` to the quality-gate issue list
- [x] 4.2 `skill/phase3_build.md`: no change needed (routes by `action`; `sliver_fin` is `warn_only`). Promote with a one-line `_ACTION_OVERRIDE` entry if builders should act on it
- [x] 4.3 `TODO.md` line 21: mark root-caused (tangent spandrel fillet running past a chamfered rib, not tessellation), link this change
