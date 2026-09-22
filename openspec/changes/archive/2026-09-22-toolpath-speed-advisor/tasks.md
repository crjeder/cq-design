## 1. Printer profile: motion block

- [x] 1.1 Add `motion` object to `src/printer_profile_schema.json` (all seven fields
      required within the object, object itself optional; `additionalProperties: false`
      matching the existing `constraints` pattern)
- [x] 1.2 Add a `motion` block with realistic PLA/Snapmaker-class defaults to
      `src/printer_profile.default.json`
- [x] 1.3 Extend `src/printer_profile_validate.py`'s write-back path to merge a stated
      `motion.<field>` override without touching unmentioned `motion` fields or top-level
      fields
- [x] 1.4 `tests/test_printer_profile_validate.py`: valid motion block, missing block still
      validates, partial motion block rejected, single-field override write-back

## 2. mesh_io: lateral area partition

- [x] 2.1 Add `lateral_area(mesh)` to `src/mesh_io.py` returning
      `A_total - A_up_facing - A_down_facing` from the same face-normal partition
      `bed_contact_mask`/`support_cost` already use
- [x] 2.2 `tests/test_mesh_io.py`: box case matches the hand-computed perimeter check from
      the design doc within a stated tolerance

## 3. toolpath_speed.py: corner model

- [x] 3.1 Re-run a part script (`exporters._load_result`) and resolve its unions
      (`units.resolve_unions`) to get each union's live authored-frame `Workplane`.
      Superseded the planned edge-hook reuse: an exact CAD-solid *section* (not a mesh
      section, and not per-edge enumeration) turned out to give LINE/CIRCLE wire edges
      with exact lengths and radii directly, with bores structurally excluded as inner
      wires -- see the corrected "B-rep edges, not mesh sectioning" note below
- [x] 3.2 `extract_corner_model`: section each union at `_N_SLICES` representative
      heights (`cadquery.Workplane.section`), walk each outer wire's edges into
      alternating wall (LINE) and corner (CIRCLE = fillet, or a synthesized vertex
      between two LINE edges = sharp) tokens, and pick the modal (most common) slice as
      the representative prismatic cross-section
- [x] 3.3 Implement `_r_eff_sharp(phi, JD)`: filleted -> its exact `edge.radius()`;
      sharp -> the junction-deviation formula from `motion.junction_deviation_mm` and
      the turn angle between consecutive wall directions
- [x] 3.4 Implement `v_corner(R_eff)` = `min(v_cruise, sqrt(a * R_eff))`
- [x] 3.5 ~~Vertical-edge/vertical-face adjacency graph~~ -- superseded by 3.1/3.2's
      section-slice approach, which gives the same (corner, wall) alternation directly
      from the section wire without needing face-adjacency bookkeeping
- [x] 3.6 Implement `T_ideal`, `T_corners` (isolated single-corner formula, summed), and
      `T_actual` (trapezoid-profile traversal via `_segment_time`, closed loop); derive
      `T_crowding` as the remainder (floored at 0); implement
      `speed_efficiency = T_ideal / T_actual`
- [x] 3.7 Implement leave-one-out per-corner attribution (`attribute_corners`,
      recomputes `T_actual` with one corner's `R_eff` set to unbounded) and the ranked
      table, only when `T_corners >= T_crowding` and `speed_efficiency` is below
      `SPEED_EFFICIENCY_REPORT_THRESHOLD`
- [x] 3.8 Implement the single feature-size-crowding finding when `T_crowding >
      T_corners` under the same threshold gate
- [x] 3.9 Implement `lateral_area`-based `P_mean`, infill path estimate, `t_layer`, the
      stall test against `motion.min_layer_time_s`, and `T_total` (stalled vs. not) in
      `layer_time_model`
- [x] 3.10 On stall, keep corner/crowding findings but rephrase rationale to
      vibration/wear and zero out any time-recovery figures; always list the three stall
      remedies (re-pose, thicken, more copies) without applying any of them
- [x] 3.11 Height-coverage floor check for the prismatic-slice assumption; emit
      `check_skipped` per-union below `HEIGHT_COVERAGE_FLOOR`
- [x] 3.12 Emit `{"status": "skipped", "reason": "...motion..."}` when
      `printer_profile.json` has no `motion`
- [x] 3.13 Emit the shared quality-gate issue contract (`severity: "warning"`) for corner
      and crowding findings; always exit 0
- [x] 3.14 CLI entry point mirroring `fem_check.py`'s argument shape
      (`--plan`, `--script`, `--stl`, `--profile`)
- [x] 3.15 `tests/test_toolpath_speed.py`: `R_eff` boundary continuity (sharp vs.
      filleted agree at the crossover), `T_ideal + T_corners + T_crowding == T_actual`
      identity, leave-one-out attribution values, stall detection true/false cases, both
      skip paths, corner findings surviving a stall with zeroed time and reworded
      rationale, bore-exclusion-via-inner-wire correctness

## 4. print_orientation.py: speed model integration

- [x] 4.1 Add `--speed-model <json>` CLI argument reading a
      `toolpath_speed.py --emit-candidates` result
- [x] 4.2 Added `toolpath_speed.evaluate_candidate_speed_models(workplane, mesh, motion,
      perimeters)`, mirroring `fem_check.evaluate_orientations`'s pattern exactly (one
      script holding both CAD and mesh precomputes a per-candidate table, keyed by
      `enumerate_candidate_normals`'s own normals; `print_orientation.py` stays
      trimesh-only and matches by normal via `_speed_lookup`, the same pattern
      `_fem_strength_lookup` uses). Each candidate rigidly transforms the union's solid
      via `placement.apply_matrix` (the same 4x4 `_rotation_to_bed` matrix the mesh
      candidate uses) and re-runs `extract_corner_model`/`compute_path_times` against
      the rotated copy -- see `design.md`'s corrected decision (a corner model is not a
      per-edge property that survives a cheap tangent rotation)
- [x] 4.3 Added `min_print_time` to `OPTIMIZE_MODES` and `_select`'s ordering: primary
      least `total_time_s` with `PRINT_TIME_BAND_S`, falling through to strength then
      support; falls back to `min_build_height`'s exact ordering when no candidate
      carries a matched speed-model entry
- [x] 4.4 Print-time fields (`total_time_s`, `speed_efficiency`, `stalled`) added to the
      chosen candidate's emitted result only when a speed-model entry matched it;
      confirmed the no-flag/no-match path is byte-identical to before
- [x] 4.5 Extended the rationale string to name the estimated time and stall state when
      matched, and to note the build-height fallback under `min_print_time` when not
- [x] 4.6 `tests/test_print_orientation.py`: `min_print_time` mode selection, fallback to
      `min_build_height` without a matched entry, presence/absence of the new result
      fields, byte-identical output with an absent/skipped speed model

## 5. Gate wiring and delivery

- [x] 5.1 Phase 3 part-authoring wiring documented in `skill/phase3_build.md` (§6.2);
      the authored-frame CLI path (`toolpath_speed.py --plan --script`, no `--stl`)
      already exists from §3
- [x] 5.2 Wired `_run_toolpath_speed_stage` into `quality_gate.py`, following
      `_run_edge_treatment_stage`'s exact pattern: reads `motion` from
      `printer_profile.json` next to the plan (absent -> `[]`, no stage run), resolves
      the single-union case's posed STL from `stl_dir` for the layer-time/stall model.
      Verified no-op (empty `motion`) is byte-identical: `test_quality_gate.py` shows no
      new failures beyond the pre-existing `manifold3d` one
- [x] 5.3 Extended `_emit_print_recipe` to add `estimated_print_time_s`,
      `speed_efficiency`, and `stalled` to the `orientation` field only when the
      `orientation` result carries `total_time_s` (i.e. `--speed-model` matched);
      absent otherwise, byte-identical to before
- [x] 5.4 `src/skill_permissions.json`: allow-pattern pair (Bash + PowerShell) for
      `toolpath_speed.py`, matching the existing `fem_check.py` entries
      (`edge_treatment_check.py` has none -- it is gate-internal only, never invoked
      directly, unlike `toolpath_speed.py`'s Phase 3 direct-invocation path)

## 6. Docs and reference

- [x] 6.1 `prompts/part.md`: new "Toolpath-speed advisor" section (mirrors the FEM
      advisor section's structure) -- when to run it, how to read `attribution` vs.
      `dominant: "crowding"`, that it's a hint pending the real orientation
- [x] 6.2 `skill/phase3_build.md`: new "Toolpath-speed advisor" section before
      print-orientation optimization (authored-frame hint), plus `--speed-model` /
      `--emit-candidates` wired into the print-orientation invocation block
- [x] 6.3 `skill/phase4_deliver.md`: reporting `estimated_print_time_s`/
      `speed_efficiency` with its stated exclusions, and the stall remedies with an
      explicit "ask before changing plate layout" checkpoint
- [x] 6.4 `reference/scripts.md`: `toolpath_speed.py` contract entry; `print_orientation.py`'s
      entry extended with `--speed-model`/`min_print_time`
- [x] 6.5 `CLAUDE.md`'s script index: added `toolpath_speed.py`, `test_toolpath_speed.py`;
      noted `mesh_io.py`'s new `lateral_area` and `print_orientation.py`'s `--speed-model`
- [x] 6.6 Injected FDM guide's Chamfer / Fillet section (`reference/FDM 3D Print Design
      Guidelines.md`): added the saturating-return framing and the feature-size-dominates
      note so the prose and the model agree; verified `test_render_prompt.py` (the closest
      thing to a condensation/injection test in this repo) still passes

## 7. Full-suite verification

- [x] 7.1 `uv run pytest tests/` -- confirmed via a pre-change baseline run (70 failed /
      952 passed / 7 skipped) and a post-change full run (70 failed / 956 passed / 7
      skipped) that the failing set is identical, all pre-existing and
      environment-caused (a missing `manifold3d` dependency), unrelated to this change;
      the four additional passes are this change's new tests. Every new/extended test
      file (`test_toolpath_speed.py`, `test_mesh_io.py`,
      `test_printer_profile_validate.py`, `test_print_orientation.py`,
      `test_quality_gate.py`) passes in full. `ruff check`/`ruff format`, `mypy`, and
      `basedpyright` clean on every changed file. (A `jsonschema`-stub mypy gap and a
      `pytest`-import basedpyright gap surfaced on files including ones I never touched
      -- `uv sync --group dev` had gone stale in this worktree's `.venv`, missing
      `types-jsonschema` and `pytest` themselves; re-syncing resolved both across the
      whole repo, not just this change's files.)
- [x] 7.2 `openspec validate toolpath-speed-advisor --strict` passes
