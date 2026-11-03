## Context

Generated scripts import STEP/BREP files directly with `cq.importers.importStep` / `importBrep`. The edit command does this in `build/edit_input.py` and `build/<stem>_edited.py`, and phase 0 rung 2 does it for found vendor files. Nothing checks the imported solid. The wrapper validates only the exported STL (trimesh watertightness and disconnected bodies). STL export welds by coordinates, so a BRep-invalid solid passes.

The 2026-11-02 spike on CADGenBench fixtures 202/217/240/250 found:

| fault | repair that worked | survives STEP round trip |
|---|---|---|
| self-intersecting wire on a B-spline face (217) | `BRepAlgoAPI_Defeaturing` of the face | yes |
| zero-area faces (250; 240 also has 5) | remove them, then `BRepBuilderAPI_Sewing(1e-2)` | yes (1e-3 leaves the shell open) |
| self-intersecting planar wire at 1e-7 (202) | raising the face tolerance | **no**: STEP drops per-edge tolerances |
| same (202) | remove the face, `BRepOffsetAPI_MakeFilling` patch, sew | BRep-valid, but fails the grader's mesh stage |
| all four | `ShapeFix_Shape`, `ShapeFix_Shell`, sewing alone, `UnifySameDomain` | no effect |

## Goals / Non-Goals

**Goals:**
- One import path for STEP/BREP that checks the solid and repairs it topologically when it is invalid.
- A volume-deviation limit that rejects a repair which changes the part noticeably. Default 1 %, configurable per call.
- BRepCheck on every wrapper run, so invalid result bodies fail loudly whatever their origin.

**Non-Goals:**
- Reproducing the grader's topology-stitched mesh gate. The cheap check stands in for it.
- Repairing 202/240-class faults. They raise `step_unrepairable` instead.
- Caching repaired files across runs.
- IGES (CadQuery has no importer).

## Decisions

**Importer lives in `blocks` (`blocks/imported.py`, exported as `blocks.import_solid`).** CLAUDE.md requires scripts to import from `blocks`, and every script already has `src` on `PYTHONPATH`. A standalone `src/repair_step.py` CLI that writes a repaired file was the alternative. It would add a file-management step to every prompt, and a second source file the edit diff would have to choose between. In-script is one line per import.

**Cheap check = `BRepCheck_Analyzer.IsValid()` and no face with area < 1e-3 mm².** BRepCheck catches 202/217/240. The zero-area test catches 250, which is BRep-valid but folds into a non-manifold mesh. Both are fast: BRepCheck takes about 1 s on 2,000 faces, and face areas come from `GProp`. The alternative, vendoring cadgenbench's mesh stitcher, was rejected because it is a large surface and tied to the grader.

**Repair ladder, cumulative, cheapest first, checked after each rung:**
1. Remove faces with area < 1e-3 mm², then sew at 1e-2 and rebuild the solid.
2. `BRepAlgoAPI_Defeaturing` of the faces BRepCheck flags.
3. Remove each flagged face, patch it with `BRepOffsetAPI_MakeFilling` over its outer-wire edges, then sew at 1e-2.

Each rung works on the previous rung's output, because 240 has both slivers and a bad face. The first result that passes the cheap check and is within the volume limit is returned. Tolerance-only fixes and `ShapeFix_Shape` are excluded: they are lost on STEP export or have no effect.

**Volume limit is a call argument, `max_volume_deviation: float = 0.01`, measured against the imported solid's volume.** A per-call argument is the smallest configurable surface. The edit command or benchmark can pass a different value without a config file. A rung that passes the check but exceeds the limit ends the ladder with `step_unrepairable`, since later rungs only remove more.

**Failure is a `cq_verify`-style marker:** `RuntimeError("[cq-verify:step_unrepairable:<file name>] <statuses, volume delta>")`. The wrapper's existing `_translate_verify_marker` turns it into a typed error once `step_unrepairable` gets an entry in `_VERIFY_HINTS`. No new transport is needed.

**Repairs are reported** as one stdout line, `[cq-design:step-repair] {"file":..., "strategy":..., "faces_removed":..., "volume_delta_pct":...}`, which surfaces in the wrapper's `stdout` field. The edit command's report quotes it. A valid import prints nothing.

**BRepCheck per run happens in the shim.** The shim holds the live `result`, so it runs BRepCheck on each body (each value of a `dict` result except `keep_out`). It writes `brep_check.json` (`{union_id: [status strings]}`) next to the STLs in the temp dir. The wrapper reads the file and adds one blocking `invalid_brep` error per failing body, with the statuses in the same `"Face: BRepCheck_..."` form the grader uses. Checking in the wrapper instead would mean importing the script a second time.

**`invalid_brep` is blocking (`success: false`) regardless of `--strict`.** An invalid BRep breaks downstream booleans and STEP consumers, so warning-only would repeat today's silent pass.

## Risks / Trade-offs

- [Existing scripts or eval cases with BRep-invalid results start failing] → run the full test suite and the eval cases during implementation. Fix or document each newly failing one before merging.
- [The cheap check passes while the grader's mesh gate fails (202's filled patch)] → accepted. The repair is still a valid BRep for CAD use. The stdout repair line makes the patch visible.
- [Volume from `GProp` is unreliable on some B-spline solids (memory: blend resize on STEP)] → compare relative deltas only. A spurious big delta fails safe, as `step_unrepairable`.
- [Repair cost is paid on every run of a script that imports a broken file (seconds on 2k faces)] → accepted for now. Mark it with a `ponytail:` comment naming caching by file hash as the upgrade path.
- [Defeaturing is slow on some parts: 1.8 s on 217, but 171 s on 240, which then still fails] → OCP's `Message_ProgressIndicator` cannot be subclassed from Python, so the call cannot be cut short. The edit command runs the wrapper with `--timeout 600` (default 180). An unrepairable input stops the edit at its first script, so the cost is paid once.
- [Sewing leaves edge/vertex bookkeeping that BRepCheck rejects (synthetic groove test)] → `_sew_solid` ends with `ShapeFix_Shape`, which moves no geometry. ShapeFix is excluded as a repair on its own, not as cleanup after sewing.
