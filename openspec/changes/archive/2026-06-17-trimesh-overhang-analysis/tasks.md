## 1. Harden overhang analysis in quality_gate.py

- [x] 1.1 In `_analyze_stl`, after the watertight/empty checks, compute the
      downward-facing mask from `tm.face_normals[:, 2] < 0` and per-face overhang
      angle `degrees(arcsin(clip(-nz, 0, 1)))`
- [x] 1.2 Build the support-needed mask for faces whose overhang angle is strictly
      greater than `overhang_deg`; skip emitting an issue when the mask is empty
- [x] 1.3 Compute `overhang_area_mm2` as the sum of `tm.area_faces` over the
      support-needed faces
- [x] 1.4 Identify the worst face (max overhang angle within the mask), set
      `worst_angle_deg`, and compute `location_xyz_mm` as the centroid of that
      face's three vertices
- [x] 1.5 Emit a single `overhang_exceeded` issue (`source: "geometry"`,
      `severity: "warning"`) carrying `overhang_area_mm2`, `worst_angle_deg`,
      `location_xyz_mm`, plus the existing `message` and `hint`
- [x] 1.6 Confirm the empty-mesh, mesh-load-error, non-watertight, and
      trimesh-missing branches still emit their existing issue types unchanged

## 2. Tests

- [x] 2.1 Add `tests/test_quality_gate.py` (or extend existing coverage) with a
      fixture STL containing a steep overhang; assert an `overhang_exceeded`
      warning is emitted with `overhang_area_mm2`, `worst_angle_deg`, and
      `location_xyz_mm`
- [x] 2.2 Add a self-supporting fixture (all faces at/below limit); assert no
      overhang issue is emitted
- [x] 2.3 Assert `worst_angle_deg`/`location_xyz_mm` track the steepest face when
      multiple faces exceed the limit
- [x] 2.4 Assert non-watertight and empty-mesh fixtures still produce the
      `non_watertight` / `invalid_geometry` errors
- [x] 2.5 Assert the trimesh-import-missing path yields a single `check_skipped`
      warning (monkeypatch the import)

## 3. Documentation cleanup

- [x] 3.1 Update the `src/quality_gate.py` row in `CLAUDE.md` to describe
      "wrapper DFM + in-process trimesh geometry/overhang analysis"; remove the
      "scad-analyzer + orca-check" wording
- [x] 3.2 Scan `CLAUDE.md` for any other orca-check / scad-analyzer / external
      slicer references in the pipeline description and remove or correct them
- [x] 3.3 Align `SKILL.md` and `README.md` quality-gate wording to "in-process
      trimesh geometry + overhang analysis (no slicer required)"
- [x] 3.4 Note in docs that real slicer-based printability validation (e.g. the
      orca-check MCP) is optional and external, not part of the gate

## 4. Verify

- [x] 4.1 Run `uv run pytest tests/test_quality_gate.py` (and the suite) green
      (test_quality_gate.py 6/6 pass; full suite 135 pass, 1 pre-existing
      unrelated failure in test_stl_to_3mf.py from missing `networkx`)
- [x] 4.2 Run `ruff check --fix` and `ruff format` on `src/quality_gate.py` and
      the new test file
- [x] 4.3 Run `openspec validate --change trimesh-overhang-analysis` clean
