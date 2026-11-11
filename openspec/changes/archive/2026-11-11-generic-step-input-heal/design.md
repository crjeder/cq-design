## Context

`blocks.import_solid` (src/blocks/imported.py) checks an imported STEP/BREP with BRepCheck plus a face-area rule (< 1e-3 mm²). It repairs a failing shape with a three-rung ladder: drop slivers and sew, defeature flagged faces, patch them with `MakeFilling`. Since a3d0fac, a repair must also pass `mesh_gate_error`.

A 2026-11-11 survey of all 32 CADGenBench edit inputs (scratch scripts, nothing committed):

| Class | Shape of the defect | Grader symptom | Fixtures |
|---|---|---|---|
| Wire tail | zero-width cusp or fold in a face boundary | `UnorientableShape` | 202, 240 |
| Sub-tolerance edge | edge shorter than its own tolerance | `UnorientableShape`, open mesh edges | 217 |
| Spot/strip face | zero-area face | BRep-valid, mesh edge shared by 4 triangles | 250, 240 (harmless in 242, 246, 248) |
| Tolerance inflation (root) | edge tol 0.005-0.09 mm | none alone; re-export flips the mesh gate | 31/32 |

All 32 files come from one OCC batch export (2026-06-03 11:17). The classes are side effects of sewing at a loose tolerance. The ladder handles 217 and 250. 202 and 240 stay `step_unrepairable`.

Spike result, verified with the dataset's own `sanity_check_submission.py` at `CADGENBENCH_REF`:

| Fixture | wire stage only | all three stages | volume change |
|---|---|---|---|
| 202 | PASS | PASS | +0.0002 % |
| 217 | FAIL | PASS | -0.03 % |
| 240 | FAIL | PASS | -0.034 % |
| 250 | PASS | PASS | -0.004 % |
| 249 (valid input) | PASS | PASS | n/a |
| 206, 215, 238 (valid inputs) | FAIL | FAIL | n/a |

The 206/215/238 failure is a grader check that `mesh_gate.py` does not port: "vertex #N: an edge endpoint node is X mm from the vertex; edge polygon orientation is inconsistent with FirstVertex/LastVertex".

## Goals / Non-Goals

**Goals:**
- One generic heal that fixes every defect class seen in the inputs, with no per-fixture logic.
- Never touch an input that already passes the grader.
- Close the gap between `mesh_gate.py` and the grader, so neither the heal nor an edit can ship a body the wrapper calls valid and the grader rejects.

**Non-Goals:**
- Edit-induced defects (`clean=False` coincident faces, pinch vertices). The existing `invalid_mesh` error and the edit loop already cover them.
- Using the `input.mesh.npz` sidecar (faceted rebuild). Kept as a possible last resort, not needed for any current fixture.
- Caching healed solids across runs.

## Decisions

**1. Trigger on the grader's criterion, not on face area.**
The check is BRepCheck valid, has a solid, and `mesh_gate_error(shape) is None`.
Alternatives: keep the sliver rule (rejected: it rewrites 242, 246 and 248, which pass, and any rewrite risks the 206-style break); BRepCheck only (rejected: misses 250).
Cost: one mesh gate on every import, already the price of every wrapper run's output check.

**2. Staged ShapeFix with opt-in modes instead of a topological ladder.**
OCC ships a fix for exactly each defect class (`FixTails`/`FixNotchedEdges`, `FixSmallEdges`, `FixSpotFace`/`FixStripFace`). They are off by default, which is why the 2026-11-02 spike's plain `ShapeFix_Shape` "fixed none". Stages run cheapest first, and the first passing stage wins, so 202 and 250 take only the wire stage and get the smallest geometry change.
Alternatives: keep defeature/patch as later rungs (rejected: the heal already covers 217 and 250, the cases they fixed; patch never produced a gate-passing result). Faceted rebuild from the sidecar mesh (rejected for now: it destroys the topology metric and is a separate decision).

**3. `heal_tol = max(0.1 mm, max edge tolerance)`.**
0.1 mm is the verified value. Tying it to the shape's own tolerance keeps the heal at the scale the defects were created at (a feature narrower than the shape's tolerance is not real geometry). For all four fixtures this resolves to 0.1 or 0.1-ish (202: max tol 0.088).
Alternative: a fixed constant (simpler, but silently too small for a coarser export).

**4. Check and return the STEP-reloaded shape.**
In-memory BRepCheck disagreed with the reloaded file in both directions: 217 is flagged in memory but passes after reload, and the earlier tolerance-only fixes passed in memory but failed after reload. The grader sees only the reloaded file, and the wrapper's per-run BRepCheck runs on whatever `import_solid` returns. Stages chain on the in-memory output (reloading between stages leaves 217 invalid), and each stage's output is round-tripped through STEP (`mesh_gate.step_roundtrip`, shared with `mesh_gate_error`) for the check only. The in-memory shape of the passing stage is returned, not the reload: exporting the reload again is invalid for 217 and 240, while exporting the in-memory shape writes exactly the file that was checked (verified with `sanity_check_submission.py`, 2026-11-11).

**5. Port the grader's edge-endpoint check into `mesh_gate._tessellate`.**
For each edge's `PolygonOnTriangulation`, compare its first and last node to `FirstVertex`/`LastVertex` (orientation-aware), with tolerance = the deflection in use. Read the grader source at `CADGENBENCH_REF` (`cadgenbench/common/mesh.py`, `validity.py`) before writing it, and match its exact rule and message rather than the paraphrase above.

## Risks / Trade-offs

- [The heal breaks a valid input] → It only runs on inputs that fail the gate, and the ported endpoint check would catch the break anyway.
- [The heal changes geometry near the defect, possibly inside the edit region] → The volume limit (1 %) stays. Observed changes are ≤ 0.034 %, and the report line states the delta.
- [Mesh gate on every import is slow for big inputs (202: about 25-50 s per gate, up to 4 gates when healing)] → Accepted. The step worker's prefix cache avoids repeats within a session. Add a hash cache (existing ponytail note) if it shows up.
- [The new endpoint check flags bodies that previously passed the wrapper] → Intended: those bodies fail the grader today. Re-run the edit fixture subset to confirm there are no false positives on known-passing outputs (cgb-merged).
- [Only four failing fixtures back the heal] → It is generic by construction (no fixture logic). Add the four as slow, opt-in regression tests when the dataset is present, and keep the synthetic tests for CI.

## Migration Plan

Pure library change, no data migration. Rollback = revert the commit. After merging, run `/cq-design:update` in benchmark workspaces so `lib/` picks up the new `imported.py` and `mesh_gate.py`, then re-run cadgenbench edit fixtures 202 and 240.

## Open Questions

- Does `FixSmallFace` on a solid with a void shell (217 has 2 shells) ever drop the inner shell? The spike result kept volume within 0.03 %, so not for 217. Watch the shell count in the regression test.
- Should a failed endpoint check at one deflection level count as a gate failure only if every level fails, the same rule as the other mesh checks? Match the grader.
