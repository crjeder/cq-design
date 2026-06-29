## Why

The geometry-level thin-wall detector silently weakens on dense meshes, so a real thin
wall on a finely tessellated part can pass the gate undetected -- a safety check that
quietly stops working exactly where the mesh has the most detail.

`measure_stl._thin_regions` ray-casts wall thickness only for a **subsampled** set of
faces (`max_samples=3000`): when `n_faces > max_samples` it strides the face index
(`idx[:: ceil(n_faces/max_samples)]`) and measures thickness for those faces only; every
unsampled face keeps `thickness = inf` (`measure_stl.py:293-311`). So `is_thin` is true
only on sampled faces. The region grouping then keeps adjacency edges where **both**
endpoints are thin (`measure_stl.py:319`) and drops any component with fewer than two
faces (`measure_stl.py:324`). Above the sample cap the sampled faces are stride-spaced and
almost never directly adjacent, so a contiguous thin wall fragments into single-face
components that are all dropped -- the detector reports nothing. Below the cap (every face
sampled) it works; above it, it silently degrades. The break is invisible: a clean result
looks identical to "no thin walls."

## What Changes

- **Make thin-region detection robust to mesh triangle density.** A contiguous thin wall
  SHALL be detected and reported as a region regardless of how finely the part is
  tessellated -- specifically, the result SHALL NOT depend on whether the face count is
  above or below the ray-cast sample cap. A thin wall that is reported at N faces SHALL
  still be reported when the same wall is remeshed to more than `max_samples` faces.
- **Preserve the ray-cast performance bound.** The fix SHALL keep the inward ray-cast
  bounded by the sample cap (it stays `O(max_samples * n_faces)`); it SHALL NOT remove the
  cap or make the per-face thickness pass scale with the full face count squared. The
  reconnection of sampled-thin faces into regions is the part that changes, not the number
  of rays cast.
- **Keep existing behavior for small meshes and the XY/Z classification.** Meshes at or
  below the cap SHALL keep producing the same regions they do today, and every reported
  region SHALL keep its existing fields (thickness, thin direction, XY/Z orientation,
  location, nearest feature, brittle flag).

## Capabilities

### Modified Capabilities
- `thin-interface-detection`: the geometry-level local-thickness requirement is extended
  with a density-robustness guarantee -- subsampling the ray-cast for performance must not
  cause a contiguous thin wall to go unreported on meshes above the sample cap.

## Impact

- Tooling: `src/measure_stl.py` -- change how sampled-thin faces are grouped into regions
  so stride-spaced samples on one physical wall reconnect (the ray-cast sampling itself is
  unchanged). Region statistics continue to be computed from the measured (sampled) faces.
- Specs: `thin-interface-detection` (modified delta) -- add a density-robustness requirement
  and scenario to the geometry-level thickness-field capability.
- Tests: `tests/test_thin_interfaces.py` / `tests/test_mesh_io.py` -- a thin wall on a mesh
  subdivided past `max_samples` is still reported; a small-mesh thin wall is unchanged; a
  uniformly thick dense mesh still reports nothing.
- Out of scope: changing the ray-cast thickness method, the `thin_max`/`wall_min`
  thresholds, the XY-vs-Z classification rule, or the sample-cap default.
