## Why

`measure_stl._thin_regions` is the top hotspot in the TODO run-time review (item 1). It casts up to 3000 inward rays in a Python loop, one `_ray_thickness` call per ray, per union, per wrapper run. Each call allocates and cross-multiplies over every half-space-prefiltered triangle, so cost scales as samples x triangles in interpreted-loop overhead.

## What Changes

- Replace the per-ray Python loop in `_sampled_thickness` with one batched `trimesh` ray query (`mesh.ray.intersects_location`, `multiple_hits=True`) over all sampled rays. trimesh selects embreex if installed, else its rtree-backed numpy intersector (rtree is already a dependency).
- Keep the exit-wall semantics: nearest hit with `n_tri . d > 0` and `t > tmin`.
- Keep the existing brute-force path as the `prefilter=False` reference used by the equivalence test.
- No change to the `measure`/wrapper JSON contract or to thin-region output.

## Capabilities

### New Capabilities

### Modified Capabilities
- `thin-interface-detection`: add a requirement that local-thickness values are independent of the ray-cast implementation and the cast is batched (no per-ray Python loop over the mesh).

## Impact

- Code: `src/measure_stl.py` (`_sampled_thickness`), `tests/test_thin_interfaces.py`.
- No new dependencies. No contract changes. Consumers: `run_cadquery_model.py`, `quality_gate.py` (via `measure`).
