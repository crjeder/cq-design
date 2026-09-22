## Why

Two of the skill's structural decisions are currently made without any stress
number behind them:

- `print_orientation.py`'s strength score is `1 - |R·load_dir · ẑ|` -- a cosine
  between a declared direction and build Z. It knows nothing about where the part
  is actually stressed, so a part whose peak stress sits in a thin web scores the
  same as one where the same load direction passes through a solid block.
- `engineering_rationale.check` is a prose string the part author derives by hand
  ("strain = 1.5*t*d/L^2 = 1.0% <= 2.0% allowable"). It picks a closed-form beam
  or cantilever formula, applies it to a shape that is usually not a beam, and is
  never executed. Nothing checks that the chosen formula fits the geometry.

Both are guesses in the places the skill most wants data: how thick a section has
to be, which way the layers should run, and where geometry needs a fillet. A
linear-static solve on the part's own STEP geometry replaces both with a stress
field -- and, critically, tells the author *where* the part is worst stressed,
which no closed-form formula in `reference/Engineering Design Rules.md` can.

The blocker so far has not been the solver but the boundary conditions: nothing in
`BUILD_PLAN.json` says how hard the load pushes, where it enters the part, or what
holds the part. `src/FEM.py` (the existing stub) guesses them from the bounding box
(`x_min` face fixed, `x_max` face loaded), which produces confident wrong numbers --
strictly worse than an honest hand formula. This change closes that gap first, then
adds the solver on top of it.

## What Changes

**Schema -- the load case becomes solvable.** `parts[].load` gains four optional
fields: `magnitude_n` (the force in newtons), `applied_at` (an `interfaces[].name`
where the load enters), `applied_dir` (a direction override for that interface, for a
load entering at an angle to the part's principal direction), and `grounded_at` (a list
of `interfaces[].name` that hold the part). All are optional and the existing
`dir`/`type` behaviour is unchanged; `applied_dir` affects the applied traction only and
nothing that reads `load.dir`. The FEM advisor runs only when magnitude and both anchors
are present and resolve to interfaces carrying `position_mm`. Anything less and it reports
why it skipped.

**Magnitude is derived from a researched mass, never invented.** The research agent
(`prompts/research.md`) gains mass as a lookup target alongside dimensions, and its
return table gains a unit column so a value in grams is expressible. The planner
converts: `F = m[g] * 9.81 / 1000 * safety_factor`, with the safety factor taken
from a new row in `reference/Engineering Design Rules.md`. A part whose load has no
researched mass behind it declares no `magnitude_n` and gets no FEM run.

**The derivation is shown at the Phase 2 checkpoint.** Every stress number downstream
scales linearly with `magnitude_n`, so the plan summary gains a load-cases table listing,
per part, the source mass, the safety factor, the resulting force, and the anchors -- the
inputs, not just the output. A wrong mass is then caught at the pause that already exists
for plan review rather than propagating into every failure index in Phase 3; a correction
there re-derives the force and lands in `request_log`. The table is omitted entirely when
no part declares `magnitude_n`.

**New `src/fem_check.py` -- an advisor, not a gate.** Tet-meshes the part's STEP
export (gmsh), solves one linear-static isotropic case (scikit-fem, pure
pip/numpy/scipy), and emits JSON:

- a **failure index** per candidate print orientation, computed by rotating the
  solved stress tensor into each candidate's build frame and taking
  `max(σ_zz/S_z, τ_z/S_shear, vm_inplane/S_inplane)` -- an anisotropic FDM
  criterion, not von Mises against a single allowable;
- **peak location and a stress-concentration ratio** `FI_max / FI_p99`, which
  separates a real overstressed section from a mesh singularity at a sharp
  re-entrant corner;
- a **geometry hint** derived from those two: a high ratio means "peak is a
  concentration at a sharp corner -- fillet it or chamfer the bearing face to
  distribute the load", a low ratio means "the section is genuinely undersized --
  thicken it".

It never exits non-zero on a high failure index. The number goes back to the part
author and to the user; no stage blocks on it.

**Mesh size is the author's call.** `--mesh-size` is required, not derived: convergence is
the one thing about an FEM result a reader must be able to interrogate, and a heuristic
default hides it. The result echoes the mesh size with node and element counts, and the
part prompt instructs the author that an implausible result is grounds to re-run smaller
and compare `fi_p99` -- moves substantially means the coarse mesh was not converged and its
number must not be cited; holds means the result is mesh-independent at that size.

**One solve, N orientations.** The solve is isotropic and runs once in the authored
frame. FDM stiffness anisotropy is ~18% (`E3/E1 = 1400/1700`), which moves the
stress field far less than the BC uncertainty already does, so re-solving per
candidate orientation buys nothing a screening advisor can use. `fem_check.py`
imports `enumerate_candidate_normals` from `print_orientation.py` so both work from
the identical candidate set.

**`print_orientation.py` takes `--fem-stress <json>`.** When given, the strength
score for each candidate is `1 - FI` from that file instead of the load-direction
cosine. Without it, scoring is exactly as today. Candidate enumeration, support
scoring, stability, and selection are untouched.

**Material constants gain the allowables FEM needs.** `reference/Engineering Design
Rules.md`'s Material Constants table gains `E`, `nu`, in-plane tensile strength,
interlayer (Z) tensile strength, and interlayer shear strength per material, plus
the default safety factor. `fem_check.py` reads these from a machine-readable
companion (`src/material_properties.json`) so the table and the solver cannot
disagree.

**`engineering_rationale.check` may cite the solve.** The field stays a string and
the existing hand-derived form stays valid; where a FEM run exists for the part, the
check SHALL cite its failure index and peak location instead of a closed-form
formula. No validation rule changes.

**Dependencies are optional.** `gmsh` and `scikit-fem` go in a new `fem` dependency
group (`uv sync --group fem`), not the default install. Absent, `fem_check.py` exits
with a structured "dependencies not installed" result and the pipeline proceeds
exactly as it does today. This keeps the default skill install unchanged in size and
keeps every existing gate pip-only.

**`src/FEM.py` is deleted**, replaced by `src/fem_check.py`. It is an unreferenced
stub: no script, prompt, spec, test, or permission entry names it.

## Capabilities

### New Capabilities
- `fem-stress-advisor`: the solve, the anisotropic failure criterion, the per-orientation
  failure index, the stress-concentration ratio and geometry hint, the advisory (never
  blocking) contract, and the degradation path when inputs or dependencies are missing.

### Modified Capabilities
- `planning-phase`: the per-part `load` may carry `magnitude_n`, `applied_at`,
  `applied_dir`, and `grounded_at`; the planner derives `magnitude_n` from a researched
  mass rather than stating a force, and declares none when no mass was researched. The
  plan-review summary gains a load-cases table showing each derivation (mass, safety
  factor, force, anchors) so it is checkable before Phase 3 runs any solve.
- `print-orientation-optimization`: the strength score MAY be the FEM failure index per
  candidate when `--fem-stress` is supplied; the declared-load cosine remains the
  behaviour without it, and the undeclared-load neutral case is unchanged.
- `engineering-rationale`: the `check` string SHALL cite the FEM failure index and peak
  location for a part that has a FEM result, and MAY remain the closed-form derivation
  otherwise.
- `reference-injection`: `reference/Engineering Design Rules.md`'s Material Constants
  section carries the elastic constants and three allowables per material plus the
  default safety factor, sourced from `src/material_properties.json`.

## Impact

- **Code**: `src/fem_check.py`, `src/material_properties.json` added;
  `src/FEM.py` deleted; `src/print_orientation.py` gains `--fem-stress`;
  `src/build_plan_schema.json` gains four `load` properties; `src/plan_summary.py` gains
  the load-cases table.
- **Prompts**: `prompts/research.md` (mass lookup target, unit column),
  `prompts/part.md` (how to run the advisor and what to cite in `check`),
  `prompts/planning.md` (deriving `magnitude_n`).
- **Skill docs**: `skill/phase1_requirements.md` (mass as a research target),
  `skill/phase2_planning.md` (load-case declaration), `skill/phase3_build.md`
  (when to run the advisor in the part loop), `reference/scripts.md`,
  `CLAUDE.md`'s script index.
- **Permissions**: `src/skill_permissions.json` gains one allow-pattern pair
  (Bash + PowerShell) for `fem_check.py`.
- **Deps**: new optional `fem` group in `pyproject.toml` (`gmsh`, `scikit-fem`).
  Default `uv sync` is unchanged.
- **Tests**: `tests/test_fem_check.py` (new; marked to skip without the `fem`
  group), `tests/test_print_orientation.py` gains the `--fem-stress` path,
  `tests/test_plan_summary.py` gains the load-cases table.
- **No gate behaviour changes.** `quality_gate.py` gains no stage. No existing
  validation rule's pass/fail changes. A model that never declares `magnitude_n`
  behaves byte-identically to today.

### Non-Goals
- Topology optimization, automatic rib generation, or any geometry the solver
  writes itself. The advisor says where and why; the part author edits.
- Nonlinear analysis, contact, buckling, fatigue, or thermal.
- Multi-part / assembly-level FEM. One part, one load case, at a time.
- Gating delivery on a failure index. Advisory in this change, and a gate is not
  a follow-on promise -- BC quality has to earn it first.
- Snap-fit strain. The closed-form cantilever check in `reference/Engineering
  Design Rules.md` fits that geometry well and stays the checked path.
