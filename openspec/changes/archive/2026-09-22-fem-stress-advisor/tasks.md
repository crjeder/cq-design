## 1. Material properties, single-sourced

- [x] 1.1 Add `src/material_properties.json`: per material (PLA, PETG, ABS, TPU 95A)
      `E_mpa`, `nu`, `s_inplane_mpa`, `s_z_mpa`, `s_shear_mpa`, plus the existing
      `allowable_strain_pct` and `flexural_modulus_gpa`, and a top-level
      `default_safety_factor`
- [x] 1.2 Extend the Material Constants table in `reference/Engineering Design Rules.md`
      with the new columns and a safety-factor row, values taken from 1.1
- [x] 1.3 Add a test asserting the Markdown table and `material_properties.json` state the
      same numbers for every material (parse the table, compare)

## 2. Schema: the solvable load case

- [x] 2.1 Add `magnitude_n` (number, exclusiveMinimum 0), `applied_at` (string),
      `applied_dir` (3-number array), and `grounded_at` (array of string, minItems 1) to
      `parts[].load` in `src/build_plan_schema.json`, all optional, with descriptions
      stating they are the FEM advisor's boundary conditions, that `magnitude_n` is
      derived from a researched mass, and that `applied_dir` overrides `load.dir` for the
      applied traction only
- [x] 2.2 Add a cross-check in `src/plan_validate.py`: a declared `applied_at` /
      `grounded_at` must name an `interfaces[].name` present on that part. Advisory on a
      plain run, consistent with the existing deferred-advisory pattern
- [x] 2.3 Extend `tests/test_plan_validate.py`: load case accepted; partial load case
      accepted; `applied_dir` accepted; `dir`-only load unchanged; anchor naming a missing
      interface reported

## 2b. Phase 2 checkpoint shows the derivation

- [x] 2b.1 `src/plan_summary.py`: render a **Load cases** table -- part ID, source mass +
      unit, safety factor, `magnitude_n`, `applied_at` (with `applied_dir` when it
      overrides), `grounded_at` -- one row per part declaring `magnitude_n`; omit the
      section entirely when none does
- [x] 2b.2 Carry the source mass and safety factor through from planning so the table can
      show the derivation, not just the force (a `planning_notes` line or the part's
      research provenance -- pick the one that does not add a schema field)
- [x] 2b.3 `skill/phase2_planning.md`: the user may correct the mass at the review pause;
      on correction re-derive `magnitude_n`, re-validate from disk, and record the
      correction via the `request_log` add path
- [x] 2b.4 `tests/test_plan_summary.py`: table rendered with the derivation columns;
      section omitted when no part declares `magnitude_n`; `applied_dir` shown only when
      it differs from `load.dir`

## 3. `src/fem_check.py`

- [x] 3.1 CLI: `fem_check.py <step> --plan BUILD_PLAN.json --part <id> --mesh-size <mm>`,
      JSON to stdout, always exit 0. `--mesh-size` is required -- no derived default
- [x] 3.2 Precondition resolution: read the part's `load`; resolve `applied_at` /
      `grounded_at` to `interfaces[]` entries with `position_mm`; resolve the material
      against `material_properties.json`. Any miss -> `{"status": "skipped", "reason": ...}`
- [x] 3.3 Dependency probe: import `gmsh` / `skfem` behind a guard; ImportError ->
      `status: "skipped"` naming the missing dependencies. Must run and skip cleanly in an
      env synced without the `fem` group
- [x] 3.4 Mesh: gmsh import of the STEP, second-order tets, at the author-supplied
      `--mesh-size`. Mesher exception -> `status: "skipped"` carrying the error
- [x] 3.5 BC assembly: nodes within each named interface's footprint (`position_mm` +
      `diameter_mm` / `size_mm`) -> fixed sets (all 3 DOF) and the loaded set;
      `magnitude_n * unit(applied_dir or load.dir)` distributed across the loaded set.
      Echo per set: interface name, node count, footprint centroid, and which direction
      was applied
- [x] 3.6 Solve: one linear-static isotropic case via `skfem` using `E_mpa` / `nu`
- [x] 3.7 Candidate orientations: import `enumerate_candidate_normals` from
      `print_orientation.py` (do not re-derive)
- [x] 3.8 Per candidate: rotate the nodal stress tensor into that candidate's build frame,
      compute `FI = max(sigma_zz/S_z, tau_z/S_shear, vm_inplane/S_inplane)` per node,
      report `fi_max` and `fi_p99`
- [x] 3.9 Concentration ratio `fi_max / fi_p99` and the geometry hint: above threshold ->
      fillet/chamfer recommendation at the peak location; at or below -> thicken /
      re-orient recommendation. Threshold as a named module constant
- [x] 3.10 Result assembly: `status`, per-candidate table (normal, `fi_max`, `fi_p99`),
      peak location in the authored frame, concentration ratio, hint, resolved BCs, the
      mesh size with node and element counts, and an explicit `assumptions` field stating
      the solve was isotropic with anisotropy applied at the criterion
- [x] 3.11 Delete `src/FEM.py`

## 4. Orientation integration

- [x] 4.1 Add `--fem-stress <json>` to `src/print_orientation.py`; when given an `ok`
      result, strength score per candidate is `1 - fi_p99` from its table
- [x] 4.2 Match candidates between the two by orientation normal within the existing
      angular dedup tolerance; an unmatched candidate falls back to the declared-load
      measure for that candidate only
- [x] 4.3 Report the strength source (`fem` | `declared_load` | `neutral`) in the
      orientation result and its rationale text
- [x] 4.4 No flag, or a `skipped` result -> byte-identical behaviour to today

## 5. Prompts and phase docs

- [x] 5.1 `prompts/research.md`: add mass as a lookup target with its source guidance, and
      add a `Unit` column to the return-contract table (the header is currently
      `Value (mm)` and cannot express grams)
- [x] 5.2 `prompts/planning.md`: how to derive `magnitude_n` from a researched mass; never
      state a force without one; add the mass to lookup targets instead of estimating
- [x] 5.3 `prompts/part.md`: when a FEM result exists, cite its failure index and peak
      location in `check` and use the solved peak for `worst_case_stress`; otherwise keep
      the closed-form derivation. Add the mesh-convergence instruction: an implausible
      result is re-run at a smaller `--mesh-size` and the two `fi_p99` values compared
      before either is cited
- [x] 5.4 `skill/phase1_requirements.md`: mass as a research target for loaded objects
- [x] 5.5 `skill/phase2_planning.md`: declaring the load case (magnitude + anchors)
- [x] 5.6 `skill/phase3_build.md`: where in the part loop the advisor runs, that it is
      advisory, how its hint feeds the next edit, and the re-run-finer convergence check

## 6. Packaging, permissions, docs

- [x] 6.1 `pyproject.toml`: optional `fem` dependency group with `gmsh` and `scikit-fem`;
      default `uv sync` unchanged
- [x] 6.2 `src/skill_permissions.json`: one allow-pattern pair (Bash + PowerShell) for
      `fem_check.py`
- [x] 6.3 `reference/scripts.md`: full contract entry for `fem_check.py` (flags, JSON
      shape, skip reasons, exit code always 0); `print_orientation.py` entry gains
      `--fem-stress`; remove nothing for `FEM.py` (it was never listed)
- [x] 6.4 `CLAUDE.md` script index: add `fem_check.py`

## 7. Tests

- [x] 7.1 `tests/test_fem_check.py`: skip-path tests run without the `fem` group --
      missing magnitude, missing anchor, anchor without `position_mm`, unknown material,
      missing dependencies; each asserts `status: "skipped"`, a reason naming the cause,
      and exit 0. Plus: omitting `--mesh-size` is an argument error, not a chosen default
- [x] 7.2 `tests/test_fem_check.py`: solve-path tests marked to skip without the `fem`
      group -- a cantilever plate under a tip load gives the highest `FI` at the root; the
      candidate placing the load across layers scores worse than the in-plane one; an
      unfilleted inner corner gives a high concentration ratio and the fillet hint, a
      uniform web gives a low ratio and the thicken hint; `applied_dir` changes the
      solved stress field where `load.dir` alone would not
- [x] 7.3 `tests/test_fem_check.py`: mesh-independence -- `fi_p99` stays comparable across
      two mesh sizes on the same part while `fi_max` may not; both runs echo their mesh
      size and element counts
- [x] 7.4 `tests/test_print_orientation.py`: `--fem-stress` with an `ok` fixture changes
      the strength scores and reports the `fem` source; a `skipped` fixture and an absent
      flag both reproduce today's scores exactly

## 8. Close-out

- [x] 8.1 Mark the TODO.md item "integrate a FEM-simulation for strength optimisation stub
      in `src/FEM.py`" done, noting the advisory scope and that gating was deliberately not
      taken
- [x] 8.2 `openspec validate --change fem-stress-advisor`
- [x] 8.3 `uv run pytest tests/` without the `fem` group (every skip path green), then with
      `uv sync --group fem` (solve paths green)
