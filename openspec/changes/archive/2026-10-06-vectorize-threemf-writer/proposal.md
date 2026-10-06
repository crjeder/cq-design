## Why

`src/exporters/threemf_multi.py` is pure-Python on every hot step: `_weld` loops per vertex with a dict, `_add_object` builds one `ET.SubElement` per vertex and per triangle, and `deliverables.py` re-opens the freshly written zip with trimesh just to count non-manifold edges. On large models this dominates 3MF export time (TODO.md Optimisation item 8).

## What Changes

- `_weld` uses `np.unique` over rounded vertex coordinates instead of a Python dict loop; vertex order stays first-seen so output is byte-identical in topology.
- `_add_object` serialises vertices and triangles with joined f-strings instead of per-element `ET.SubElement`.
- `write_named_3mf` / `write_single_3mf` compute the non-manifold edge count from the welded in-memory triangle arrays (reusing `mesh_io`'s edge-count logic) and `write_named_3mf` returns it; `deliverables.py` uses that return value instead of re-parsing the zip.
- `count_nonmanifold_edges(path)` stays as the independent from-file check used by `quality_gate.py` and tests.
- No change to the 3MF file contents, plate metadata, or public signatures beyond the added return value.

## Capabilities

### New Capabilities

### Modified Capabilities

- `model-export`: adds a requirement pinning the 3MF writer's welded, manifold output and its in-memory non-manifold count (previously unspecified); file contents are unchanged.

## Impact

- Code: `src/exporters/threemf_multi.py`, `src/deliverables.py`.
- Tests: `tests/test_exporters.py`, `tests/test_assembly_and_deliverables.py` (existing manifold assertions keep passing; add an equivalence test for the new `_weld`).
- Docs: `TODO.md` item 8 ticked; `reference/scripts.md` deliverables row unaffected.
- No new dependencies (numpy already required by trimesh).
