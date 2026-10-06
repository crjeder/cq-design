## Context

`threemf_multi.py` welds vertices with a Python dict loop, emits one `ET.SubElement` per vertex/triangle, and `deliverables.write_3mf` reloads the zip with trimesh to count non-manifold edges. Static read only; not profiled. `quality_gate._analyze_3mf` and two tests also call `count_nonmanifold_edges(path)`.

## Goals / Non-Goals

**Goals:**
- Same 3MF topology and plate metadata, less Python-loop time on large meshes.
- Drop the post-write zip re-parse in `deliverables.py`.

**Non-Goals:**
- Changing tessellation tolerance or single-tessellation reuse (TODO item 7).
- Removing `count_nonmanifold_edges(path)`: the gate keeps an independent from-file check.

## Decisions

- **Weld**: `pts = np.array([v.toTuple() for v in verts])`, `np.unique(np.round(pts, 6), axis=0, return_index=True, return_inverse=True)`, then renumber unique ids by first-occurrence order (`argsort` of the first-index array) so vertex order matches the old dict loop. Keep the first-seen original coordinates (not rounded) as output, as before. Alternative (skip renumbering) rejected: changes vertex order for no gain and complicates an equivalence test.
- **XML**: build each object's `<mesh>` body as joined f-strings (floats via `.tolist()` so `str(float)` matches today). Keep `ET` for the small skeleton and splice the pre-built mesh text in when serialising in `_write_zip`; no per-vertex/triangle Elements.
- **Count**: after welding, `edges = np.sort(tris[:, [0,1,1,2,2,0]].reshape(-1, 2), axis=1)`, `np.unique(..., axis=0, return_counts=True)`, count `!= 2`. Same rule as `mesh_io.nonmanifold_edge_count` but on raw arrays, avoiding a trimesh Trimesh build. Summed across objects (edges are per-object since indices are per-object). `_add_object` returns its count; writers return the sum.
- **Caller**: `deliverables.write_3mf` uses the returned count; the `ImportError` fallback goes away since numpy is already a hard dependency of the exporter path.

## Risks / Trade-offs

- Float format drift in XML (`str(v.x)` vs numpy repr): mitigated by formatting from Python floats via `.tolist()`, matching `str(float)`.
- The returned count no longer proves the on-disk file parses back identically; `quality_gate._analyze_3mf` still does the from-file check, so end-to-end coverage remains.
