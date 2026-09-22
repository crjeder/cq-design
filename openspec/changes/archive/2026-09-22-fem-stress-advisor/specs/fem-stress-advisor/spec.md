## ADDED Requirements

### Requirement: A FEM advisor solves a declared load case on the part's STEP geometry

The system SHALL provide `src/fem_check.py`, which tet-meshes a part's exported STEP
geometry, solves one linear-static isotropic load case, and emits a JSON result to
stdout. The script SHALL take the part's STEP file, `BUILD_PLAN.json`, and the part id,
and SHALL derive every boundary condition from the part's declared `load` -- never from
the bounding box, the geometry, or any other inference.

The result SHALL always carry `status` (`"ok"` or `"skipped"`), and on `"ok"` SHALL
carry the per-orientation failure-index table, the peak location, the concentration
ratio, the geometry hint, and the resolved boundary conditions described in the
requirements below.

#### Scenario: A part with a complete load case is solved
- **WHEN** `fem_check.py` runs on a part whose `load` declares `magnitude_n`,
  `applied_at`, and `grounded_at`, and whose named interfaces carry `position_mm`
- **THEN** the result has `status: "ok"` and carries a failure index for every candidate
  orientation, the peak stress location, and a geometry hint

#### Scenario: Boundary conditions are never inferred from geometry
- **WHEN** any part is analysed
- **THEN** the fixed and loaded node sets are resolved only from the interfaces named by
  `grounded_at` and `applied_at`, and no bounding-box face, largest face, or other
  geometric heuristic contributes to either set

### Requirement: Boundary conditions resolve from named interfaces

The load's `applied_at` SHALL name one `interfaces[].name` on the part and `grounded_at`
SHALL name one or more. Each named interface SHALL resolve to a footprint from its
`position_mm` together with its `diameter_mm` or `size_mm`; mesh nodes within that
footprint form the loaded set (for `applied_at`) or the fully fixed set (for
`grounded_at`). The load SHALL be applied as `magnitude_n` distributed over the loaded
set in the direction of the part's `load.dir`, or of `load.applied_dir` when that
per-interface override is declared. `grounded_at` interfaces take no direction: they are
fully fixed.

The result SHALL echo, for each resolved set, the interface name, the node count, and the
footprint centroid, so the author can see what was actually fixed and loaded.

#### Scenario: Named interface resolves to a node set
- **WHEN** `grounded_at: ["wall_screws"]` names an interface with `position_mm` and
  `diameter_mm`
- **THEN** the nodes inside that footprint are constrained in all three translational
  degrees of freedom, and the result reports that set's node count and centroid

#### Scenario: Load magnitude is distributed, not applied at a point
- **WHEN** a load of `magnitude_n` is applied at an interface resolving to N nodes
- **THEN** the total applied force equals `magnitude_n` in the `load.dir` direction,
  distributed across those N nodes

#### Scenario: Per-interface direction override
- **WHEN** the part declares `load.applied_dir` differing from `load.dir`
- **THEN** the traction is applied along `applied_dir`, and the result echoes which
  direction was used so the applied direction is never ambiguous

### Requirement: Mesh size is chosen by the author and the result is re-runnable

`fem_check.py` SHALL take the mesh size as a required `--mesh-size <mm>` argument rather
than deriving a default. The result SHALL echo the mesh size together with the resulting
node and element counts, so the author can judge whether the discretisation supports the
number reported.

`prompts/part.md` and `skill/phase3_build.md` SHALL instruct the author that an implausible
result -- an extreme concentration ratio, a failure index far from what the geometry
suggests, or a peak at an unexpected location -- is grounds to re-run at a smaller mesh
size and compare: a `fi_p99` that moves substantially between the two runs means the
coarser mesh was not converged and its number SHALL NOT be cited; a `fi_p99` that holds
means the result is mesh-independent at that size.

#### Scenario: Mesh size must be stated
- **WHEN** `fem_check.py` is invoked without `--mesh-size`
- **THEN** it reports the missing argument rather than choosing a size on the author's
  behalf

#### Scenario: Result carries its discretisation
- **WHEN** a solve completes
- **THEN** the result states the mesh size used and the resulting node and element counts

#### Scenario: Implausible result is re-run finer
- **WHEN** a result's concentration ratio or failure index does not match what the geometry
  suggests
- **THEN** the author re-runs at a smaller mesh size and compares `fi_p99` between the two
  runs before citing either number

### Requirement: The failure criterion is anisotropic and evaluated per candidate orientation

The system SHALL solve once, isotropically, in the part's authored frame, and SHALL then
evaluate the failure index for each candidate print orientation by rotating the solved
stress tensor into that candidate's build frame. The candidate set SHALL be the one
enumerated by `src/print_orientation.py`, imported rather than re-derived, so both tools
index the identical list.

For each candidate, with `z` the candidate's build direction, the failure index SHALL be

```
FI = max( sigma_zz / S_z, tau_z / S_shear, vm_inplane / S_inplane )
```

where `S_z`, `S_shear`, and `S_inplane` are the interlayer tensile, interlayer shear, and
in-plane tensile allowables for the plan's material. The system SHALL NOT compare a von
Mises equivalent stress against an interlayer allowable.

The result SHALL state, as an explicit field, that the solve was isotropic and that the
material anisotropy enters at the criterion, so no consumer reads the failure index as a
certified value.

#### Scenario: Interlayer tension dominates an across-layer load
- **WHEN** a candidate orientation places the load direction along build Z
- **THEN** that candidate's failure index is driven by the `sigma_zz / S_z` term and is
  higher than a candidate placing the same load in the layer plane

#### Scenario: One solve serves every candidate
- **WHEN** N candidate orientations are evaluated
- **THEN** exactly one linear-static solve is performed, and the N failure indices are
  computed by rotating that solve's stress tensor

#### Scenario: Candidate sets cannot drift apart
- **WHEN** the candidate enumeration in `print_orientation.py` changes
- **THEN** the failure-index table changes with it, because `fem_check.py` imports that
  enumeration rather than carrying its own

### Requirement: The concentration ratio distinguishes a sharp corner from a thin section

The result SHALL carry both `fi_max` and `fi_p99` (the 99th-percentile nodal failure
index) and their ratio. A ratio above the concentration threshold SHALL be reported as a
stress concentration -- the peak is confined to a small neighbourhood, characteristic of a
sharp re-entrant corner rather than an overstressed section -- and the geometry hint SHALL
recommend filleting the concave edge or chamfering the bearing face so the load
distributes. A ratio at or below the threshold SHALL be reported as a distributed stress
and the hint SHALL recommend thickening the section or comparing the candidate table for a
better orientation.

Any per-orientation strength value consumed downstream SHALL be derived from `fi_p99`,
which is mesh-insensitive, not from `fi_max`.

#### Scenario: Unfilleted internal corner
- **WHEN** the peak failure index is confined to nodes around a sharp concave edge, giving
  a high `fi_max / fi_p99` ratio
- **THEN** the result reports a stress concentration and the hint recommends a fillet or a
  load-distributing chamfer, not a thicker section

#### Scenario: Genuinely undersized web
- **WHEN** the elevated failure index is spread across a real volume, giving a low ratio
- **THEN** the result reports a distributed stress and the hint recommends thickening the
  section or re-orienting

#### Scenario: Mesh refinement does not move the reported strength
- **WHEN** the same part is analysed at two mesh sizes
- **THEN** `fi_max` may differ substantially at a sharp corner while the value consumed
  downstream, `fi_p99`, stays comparable

### Requirement: The advisor never blocks

`fem_check.py` SHALL exit 0 on any failure index, however high. It SHALL NOT be added as a
`src/quality_gate.py` stage, and no phase SHALL block on its result. The result SHALL reach
the part author in the Phase 3 loop and the user at the relevant checkpoint; the decision
to act on it belongs to the author.

#### Scenario: Failure index above the allowable
- **WHEN** a solve reports a failure index greater than 1.0
- **THEN** `fem_check.py` exits 0, the quality gate is unaffected, and the number and hint
  are surfaced to the part author

#### Scenario: No gate stage is added
- **WHEN** `quality_gate.py` runs
- **THEN** it performs no FEM analysis and its set of stages is unchanged by this
  capability

### Requirement: Missing inputs and missing dependencies degrade to a stated skip

When the part declares no `magnitude_n`, no `applied_at`, or no `grounded_at`; when a named
interface does not exist or carries no `position_mm`; when meshing fails; or when the
optional `fem` dependency group is not installed, `fem_check.py` SHALL emit
`status: "skipped"` with a `reason` naming which input or dependency was missing, and SHALL
exit 0.

The `gmsh` and `scikit-fem` dependencies SHALL live in an optional `fem` dependency group,
not in the default install, so the default `uv sync` and every existing check remain
pip-only and unchanged in size.

#### Scenario: Part declares no load magnitude
- **WHEN** a part's `load` carries `dir` and `type` but no `magnitude_n`
- **THEN** the result is `status: "skipped"` with a reason naming the missing magnitude,
  exit 0, and no solve is attempted

#### Scenario: Anchor names an interface without a position
- **WHEN** `grounded_at` names an interface that exists but carries no `position_mm`
- **THEN** the result is `status: "skipped"` naming that interface, and no footprint is
  guessed for it

#### Scenario: FEM dependencies not installed
- **WHEN** `fem_check.py` runs in an environment synced without the `fem` group
- **THEN** it emits `status: "skipped"` reporting the missing dependencies, exits 0, and
  the pipeline proceeds exactly as it does without this capability

#### Scenario: Meshing fails
- **WHEN** gmsh cannot mesh the part's STEP geometry
- **THEN** the result is `status: "skipped"` carrying the mesher's error as the reason, and
  the pipeline is not interrupted

### Requirement: Material allowables have one machine-readable source

The elastic constants and the three allowables per material SHALL live in
`src/material_properties.json`, which `fem_check.py` reads. The Material Constants table in
`reference/Engineering Design Rules.md` SHALL be derived from that file rather than
maintained independently, and a test SHALL assert the two agree.

#### Scenario: Table and solver cannot disagree
- **WHEN** a material's interlayer allowable is changed
- **THEN** it is changed in `src/material_properties.json`, the injected reference table
  reflects the same value, and the test asserting their agreement passes

#### Scenario: Material not in the table
- **WHEN** the plan declares a material with no entry in `src/material_properties.json`
- **THEN** the result is `status: "skipped"` naming the material, rather than substituting
  another material's constants
