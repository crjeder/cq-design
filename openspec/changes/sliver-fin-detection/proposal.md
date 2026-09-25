## Why

A hand-built part (Katzenwendeltreppe `step_rim_fillet.py`: rim fillet as a revolved spandrel, rib fillets as extruded spandrel prisms, all unioned onto tapering ribs) produced spikes in the STL and in the slicer. The B-Rep was valid, the mesh was watertight, volume matched the B-Rep to 0.003%, and no existing gate objected. Re-tessellating 75x finer (683k triangles) left the defects unchanged, so they are geometry, not tessellation: four zero-thickness fins (adjacent faces with opposite normals, 179.7 degree fold) plus knife-edge wedges (135 degree folds), where a hand-built tangent (spandrel) fillet prism keeps running past the wall it sits on. Its arc meets the rib flank tangentially, so its tip is a zero-thickness cusp; the rib tapers and has a 0.6 mm bottom chamfer, so beyond about 154 mm the cusp hangs free below the rib. Overlapping the prism further into the neighbouring torus does not help; ending it where the rib is still two fillets deep leaves zero fins (verified).

Nothing in the gate can see this class. `non_watertight` needs an open edge; `overhang_exceeded` looks at face direction, not at faces folding back on each other; `script_lint`/`cq_verify` reason about the script, not the solid. A hand-built fillet that fails to mate is therefore indistinguishable from a good one until a slicer draws it.

## What Changes

- New mesh metric `mesh_io.fold_metrics(mesh, min_interior_deg)`: for every pair of adjacent triangles, the interior dihedral angle (180 degrees minus the angle between their normals). Pairs below the threshold are folds. Returns the count, the sharpest interior angle, its location, and the smallest face area involved, clustered so one fin reports once.
- New quality-gate finding `sliver_fin` emitted from `_analyze_stl` (same pass as `non_watertight` and `overhang_exceeded`, same `{source, severity, type, message, hint, ...}` contract): `warning` when any fold has an interior angle below 10 degrees.
- The hint names the usual cause and the fix: a tangent (spandrel/prism) fillet whose razor-thin tip runs past the wall it sits on (tapered or chamfered ribs), or solids ending flush; end the fillet where the wall is deeper than the fillet radius plus any chamfer, or use `.edges(...).fillet()` on the selected edge.
- Location is reported in the build frame, matching `overhang_exceeded`.
- `reference/scripts.md` documents the new issue. It routes as `warn_only` (severity default); `skill/phase3_build.md` already routes by `action`, so it needs no change.

## Capabilities

### New Capabilities
- `sliver-fin-detection`: mesh-level detection of near-zero-thickness fins and knife-edge folds in an exported part STL, reported as an advisory gate finding.

### Modified Capabilities

## Impact

`src/mesh_io.py` (new `fold_metrics`), `src/quality_gate.py` (`_analyze_stl`), `reference/scripts.md`, `TODO.md` (line 21 marked root-caused), tests (`tests/test_mesh_io.py`, `tests/test_quality_gate.py`, one CadQuery fixture reproducing the four fins). JSON output contract unchanged: one new `type` value in the existing `issues` list. No new dependency (trimesh already required).

Out of scope: changing the tessellator (measured not to be the cause), repairing the offending geometry automatically, and per-face triangle quality (aspect ratio), which is harmless to slicers on planar faces.
