## Context

Rung 3 delivers a found STL unmodified. Its vetting is: (1) `measure_stl.py` dimension
cross-check, (2) "the quality gate's mesh-level stages", (3) user confirmation. Step 2 has no
runnable command: `quality_gate.py` needs a part script and `BUILD_PLAN.json`, and rung 3
produces neither ("no `BUILD_PLAN.json` is produced"). The two mesh-level checks the step
names already exist as standalone tools that take a bare STL:

- `measure_stl.py <stl>` emits `is_watertight` (`src/measure_stl.py:426`) -- step 1 already
  runs it.
- `print_orientation.py <stl> --overhang-max-deg <n>` (`src/print_orientation.py:652-658`)
  scores every candidate pose with `mesh_io.support_cost`, the same overhang definition the
  gate uses (`mesh_io.overhang_metrics`), and emits `support_score` (0 = no unsupported
  overhang past the limit) and `rotate` for the chosen pose.

## Goals / Non-Goals

**Goals:**
- Every rung-3 vetting step names an exact, runnable command.
- Pass/fail matches the severity a generated STL gets from the gate.

**Non-Goals:**
- Making `quality_gate.py` accept a bare mesh (no `--script`/`--plan`). Two existing tools
  cover it; a new gate mode would duplicate them.
- Sliver-fin or other gate stages beyond watertightness and overhang -- step 2 names only
  those two.

## Decisions

- **Watertightness from step 1's output, not a new run.** `is_watertight` is already in the
  `measure_stl.py` JSON. Re-running anything for it is waste.
- **`--optimize-for min_support`.** The default `strength` mode ranks strength first, so its
  chosen pose is not guaranteed to be the least-support pose. A found mesh has no declared
  load, so the question is only "can this print without support in its best pose" --
  `min_support` answers that directly.
- **Threshold from `profile.json` `constraints.overhang_max_deg`.** No plan exists at rung 3;
  the profile is the same source the plan's constraint is seeded from (`init_permissions.py`
  seeds `profile.json` per working directory).
- **Overhang is a finding, not a rejection.** The gate reports overhang as `severity:
  warning` (`src/quality_gate.py` `_analyze_stl`) and `non_watertight` as `error`. Rung 3's
  promise is "the same checks any generated STL passes", so: `is_watertight: false` fails
  rung 3; `support_score > 0` is shown to the user at step 3 (with the pose's `rotate`) and
  the user decides. Alternative considered: reject on any support -- rejected as stricter
  than generated parts and as discarding most real-world found meshes.

## Risks / Trade-offs

- [`print_orientation.py` exits non-zero on an unloadable mesh (`mesh_io.load_mesh` raises)]
  -> treat a load failure the same as `is_watertight: false`: rung 3 does not fit.
- [`support_score` is severity-weighted, not an area] -> present it as "needs support /
  doesn't", not as mm^2; the user sees the preview/link anyway.
