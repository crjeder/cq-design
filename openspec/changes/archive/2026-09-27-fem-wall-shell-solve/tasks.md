## 1. Printer profile schema: `top_bottom_layers`

- [x] 1.1 Add `constraints.top_bottom_layers` (integer, minimum 1, optional) to
      `src/printer_profile_schema.json`, following the existing `bridge_max_mm` pattern.
- [x] 1.2 `src/printer_profile_validate.py`: confirm default-application/write-back handles
      the new optional field (add explicit handling only if the existing generic
      optional-field logic doesn't already cover it). Confirmed: `write_profile_fields` is
      fully generic (merges any dotted/top-level key then re-validates) -- no change needed.
- [x] 1.3 Leave `src/printer_profile.default.json` without the field (so it exercises the
      default-when-absent path) -- confirmed, no edit needed.
- [x] 1.4 `tests/test_printer_profile_validate.py`: add cases for a valid
      `top_bottom_layers`, a missing one (defaults, still validates), and a `0`/negative
      one (rejected).

## 2. `quality_gate.py`: read real settings instead of hardcoded/re-derived ones

- [x] 2.1 `_emit_print_recipe`: replace the hardcoded `top_bottom_layers: 4` literal with
      `constraints.get("top_bottom_layers", 4)`.
- [x] 2.2 `_emit_print_recipe`: replace `layer_height_mm = round(nozzle * 0.5, 2)` with a
      read of `printer_profile.json`'s `motion.layer_height_mm`. Correction from the
      design doc: `motion` is never part of `BUILD_PLAN.json` (top-level
      `additionalProperties: false`, no `motion` property declared) -- it only exists in
      `printer_profile.json` on disk, read the same way `_run_toolpath_speed_stage`
      already does. `_emit_print_recipe` gained a `plan_path: str | None` parameter for
      this; the one call site (`run_gate`) already has `plan_path` in scope.
- [x] 2.3 Confirmed: existing `test_print_recipe_supports_*` tests in
      `tests/test_quality_gate.py` still pass unchanged (`uv run pytest
      tests/test_quality_gate.py -k recipe` -- 7 passed).
- [x] 2.4 Added direct unit tests for `_emit_print_recipe`: default fallback (no profile),
      `constraints.top_bottom_layers` override, `motion.layer_height_mm` override, and no
      `plan_path` given.

## 3. `fem_check.py`: hollow-shell geometry

- [x] 3.1 `mesh_step`: capture `importShapes`'s returned `outDimTags`, filter to `dim == 3`
      solid volume tag(s).
- [x] 3.2 **Corrected during implementation** (see design.md's "Correction during
      implementation"): a bare `addThickSolid(tag, [], +offset)` does not hollow the solid
      -- verified with a controlled bounding-box check that it returns an offset
      *duplicate* (grown outward for positive offset, shrunk inward for negative), never
      "the wall material between old and new surface". The actual construction is:
      `addThickSolid(tag, [], -wall_thickness_mm)` (negative) to get the inward-offset
      cavity solid, then `occ.cut([(3, tag)], cavity, removeTool=True)` to subtract it from
      the original -- confirmed by bounding-box comparison (matches the original part
      exactly) and by confirming every meshed node is tet-referenced (zero orphans).
- [x] 3.3 `cut(..., removeTool=True)` consumes both the original and the cavity tool by
      default, so no separate `gmsh.model.occ.remove` call is needed; `synchronize()` then
      mesh as before.
- [x] 3.4 Multi-solid-STEP case: the loop shells each returned solid volume tag
      independently (task 3.2), so N solids get N independently-shelled bodies, each with
      the same uniform thickness -- no special-casing needed; not verified against a real
      multi-union STEP fixture (none of the existing FEM test fixtures are multi-solid),
      flagged as a residual gap for whoever hits it first.
- [x] 3.5 No new `try/except` needed: `addThickSolid`/`remove`/`synchronize` all run
      inside `mesh_step`'s existing `try/finally` (finalizes gmsh either way), and
      `run_fem_check`'s existing `except Exception as e: return _skip(f"gmsh meshing
      failed: {e}")` around the `mesh_step(...)` call already catches anything `mesh_step`
      raises, including a degenerate/self-intersecting `addThickSolid`.
- [x] 3.6 `run_fem_check`: resolves `wall_mm`/`topbot_mm` via new `_resolve_shell_thicknesses`,
      threads `wall_mm` into `mesh_step`, and echoes it as `mesh.shell_thickness_mm` in the
      result.

## 4. `fem_check.py`: thickness-mismatch warning

- [x] 4.1 `_resolve_shell_thicknesses` computes `topbot_mm = top_bottom_layers *
      layer_height_mm`. Corrected from the original task wording: `fem_check.py` needed a
      new `plan_path: str | None` parameter (threaded through `run_fem_check` and `main()`,
      same as `_emit_print_recipe`'s) to read `printer_profile.json`'s `motion` block next
      to the plan -- without it, `fem_check.py`'s number could silently diverge from
      `_emit_print_recipe`'s for a profile declaring a non-default `motion.layer_height_mm`,
      which the design doc explicitly said should never happen. Falls back to
      `nozzle_mm * 0.5` when no `motion` block or no `plan_path`, matching
      `_emit_print_recipe`'s own fallback.
- [x] 4.2 `_thickness_mismatch_warning` computes `pct_diff = abs(wall_mm - topbot_mm) /
      max(wall_mm, topbot_mm)`; adds `thickness_mismatch_warning` to the result when
      `> 0.25`, omits it otherwise.
- [x] 4.3 `tests/test_fem_check.py`: added cases for divergent thickness (warning present,
      correct values), matching thickness (warning absent), and the profile
      `motion.layer_height_mm` override.

## 5. Verification

- [x] 5.1 Full suite (`uv run pytest tests/`, `fem` group synced): **1110 passed, 1
      skipped**, no regressions.
- [x] 5.2 No eval-corpus case declares a solvable FEM load case (`applied_at`/
      `grounded_at`) -- grepped `evals/cases/**/BUILD_PLAN.json` for `"applied_at"`, no
      matches -- so this couldn't be run against real corpus data as scoped. Substituted:
      `tests/test_fem_check.py`'s solve-path tests exercise exactly this scenario (a
      cantilever with a full load case) end-to-end against the corrected hollow-shell
      mesh, including the resolved boundary-condition footprints, mesh-independence check,
      and concentration ratio -- all 24 pass.
- [x] 5.3 `skill/phase3_build.md`'s FEM stress advisor section: noted the shell is now the
      thinnest feature by construction, `mesh.shell_thickness_mm` is the value to pick
      `--mesh-size` as a fraction of, and a mesh size comparable to or larger than the
      shell thickness risks a singular solve.
