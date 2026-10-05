## Why

`measure_stl._thin_regions` casts one inward ray per sampled face and, for each ray, runs Moeller-Trumbore (two `np.cross` plus several `einsum`s) against every triangle in a Python loop. Per ray, only triangles facing along the ray direction (`n_tri . d > 0`) and lying in front of the origin can be the nearest forward hit on a watertight mesh, so roughly half or more of that work is wasted on every iteration of the part loop.

## What Changes

- Precompute triangle normals once and evaluate the facing test for all sampled rays in one matrix product (`N @ D.T`).
- Run Moeller-Trumbore only on each ray's surviving triangle subset (facing plus in-front half-space).
- Result is unchanged: same thickness per face, same regions, same JSON. No new dependency, no `rtree`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `thin-interface-detection`: add a requirement that the ray-cast pre-filter must not change reported thickness (behavior-preserving guarantee).

## Impact

- `src/measure_stl.py`: `_ray_thickness` and the loop in `_thin_regions`.
- `tests/test_thin_interfaces.py`: equivalence test against the unfiltered cast.
- No change to the wrapper JSON contract, `thin_max`/`wall_min` semantics, or the sample cap.
