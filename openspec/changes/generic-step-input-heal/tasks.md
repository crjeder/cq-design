## 1. Grader endpoint check in the mesh gate

- [x] 1.1 Read the grader's mesh/validity source at `CADGENBENCH_REF` (`cadgenbench/common/mesh.py`, `validity.py`; from the uv cache or the pinned GitHub commit) and note the exact edge-endpoint rule, its tolerance and its message
- [x] 1.2 (check already present in `_tessellate`; message aligned with the grader's) Add the edge-polygon endpoint vs `FirstVertex`/`LastVertex` check to `src/mesh_gate.py` `_tessellate`, raising `MeshGateError` with the grader's message
- [x] 1.3 Test: a body whose healed export reproduces the endpoint mismatch (or a synthetic one) makes `mesh_gate_error` return the endpoint reason; an ordinary filleted box still passes

## 2. Grader-criterion check in import_solid

- [x] 2.1 Replace `_problems` in `src/blocks/imported.py` with BRepCheck + has-solid + `mesh_gate_error`, run on the STEP-reloaded shape, and drop the face-area rule
- [x] 2.2 Add a STEP round-trip helper (reuse the export/import in `mesh_gate_error`; no second copy)
- [x] 2.3 Test: a valid solid with a < 1e-3 mm² face that passes the gate is returned unchanged, with nothing printed

## 3. Staged ShapeFix heal

- [x] 3.1 Implement the `wire`, `small_edges` and `small_faces` stages with `heal_tol = max(0.1, max edge tolerance)`, checking the reloaded output after each and returning the first passing reloaded shape within the volume limit
- [x] 3.2 Remove `_drop_slivers`, `_defeature`, `_patch`, `_slivers`, `_flagged` and any sew/solid helpers left unused; update the module docstring
- [x] 3.3 Report line: `strategy` lists stages, add `heal_tol_mm`, drop `faces_removed`; `step_unrepairable` detail names the stages tried and the last reason
- [x] 3.4 Update `tests/test_import_solid.py`: the sliver-slab tests now expect no repair (or are rebuilt around a defect the gate fails); keep the volume-limit, mesh-gate-monkeypatch and missing-face unrepairable tests
- [x] 3.5 Add a synthetic tail-defect test if a small one can be built (a face wire with a zero-width spike); otherwise skip it and rely on 3.6 (skipped: no small synthetic spike; covered by 3.6)
- [x] 3.6 Add a slow test, skipped when `evals/runs/cadgenbench-data` is absent, that imports 202, 217, 240 and 250 and asserts that each heals within 0.05 % volume and that 206 is returned unchanged

## 4. Docs and contracts

- [x] 4.1 Update `reference/scripts.md` (`import_solid` and `mesh_gate` contract entries)
- [x] 4.2 Update the rung/sliver wording in `commands/edit.md` and `skill/phase0_sourcing.md`
- [x] 4.3 Run `ruff check --fix`, `ruff format` and `uv run pytest tests/test_import_solid.py tests/test_edit_command.py` plus the mesh-gate tests

## 5. Benchmark verification

- [x] 5.1 Export the healed inputs for 202, 217, 240 and 250 through `import_solid` and run the dataset's `sanity_check_submission.py` on each (all PASS)
- [x] 5.2 Re-run the cadgenbench edit fixtures 202 and 240 with `evals/cadgenbench_run.py --fixtures 202,240` and record the sanity results (2026-11-11, reinstalled plugin: 202 PASS, 240 PASS)
- [x] 5.3 Run the new mesh gate over the cgb-merged edit outputs that currently pass and confirm there are no new `invalid_mesh` reasons
