## MODIFIED Requirements

### Requirement: A FEM advisor solves a declared load case on the part's STEP geometry

The system SHALL provide `src/fem_check.py`, which builds a hollow-shell volume from a
part's exported STEP geometry, tet-meshes that shell, solves one linear-static isotropic
load case, and emits a JSON result to stdout. The script SHALL take the part's STEP file,
`BUILD_PLAN.json`, and the part id, and SHALL derive every boundary condition from the
part's declared `load` -- never from the bounding box, the geometry, or any other
inference.

The hollow-shell volume SHALL be built with one uniform wall thickness applied to every
face of the part alike -- vertical and horizontal faces are not distinguished -- sourced
from the plan's printer profile `constraints.wall_min_mm`, so the solve reflects only the
material the slicer will actually lay down solid (the shell), never the sparse infill
interior.

The result SHALL always carry `status` (`"ok"` or `"skipped"`), and on `"ok"` SHALL
carry the per-orientation failure-index table, the peak location, the concentration
ratio, the geometry hint, the resolved boundary conditions, and the resolved shell
thickness described in the requirements below.

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

#### Scenario: Only the wall-thickness shell is meshed
- **WHEN** `fem_check.py` solves a part
- **THEN** the solved volume is a hollow shell of the profile's `constraints.wall_min_mm`
  thickness, not the part's full solid volume, and the result states the thickness used

#### Scenario: Shell thickness is uniform across the part
- **WHEN** a part has both near-vertical and near-horizontal faces
- **THEN** both get the same shell thickness -- `constraints.wall_min_mm` -- with no
  face-normal-dependent split

### Requirement: Missing inputs and missing dependencies degrade to a stated skip

When the part declares no `magnitude_n`, no `applied_at`, or no `grounded_at`; when a named
interface does not exist or carries no `position_mm`; when meshing fails; when the
hollow-shell volume cannot be constructed (for example, a local feature thinner than the
shell thickness produces a self-intersecting or degenerate offset); or when the optional
`fem` dependency group is not installed, `fem_check.py` SHALL emit `status: "skipped"` with
a `reason` naming which input or dependency was missing, and SHALL exit 0.

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

#### Scenario: Shell construction fails on a thin local feature
- **WHEN** a part has a local feature thinner than twice the profile's `wall_min_mm`, and
  building the hollow-shell volume produces self-intersecting or degenerate geometry
- **THEN** the result is `status: "skipped"` carrying the shell-construction failure as the
  reason, and the pipeline is not interrupted

## ADDED Requirements

### Requirement: A thickness-mismatch warning flags a questionable uniform-thickness assumption

The result SHALL carry a `thickness_mismatch_warning` field whenever the profile's wall
thickness (`constraints.wall_min_mm`) and its top/bottom shell thickness
(`constraints.top_bottom_layers` times the layer height) differ by more than 25%, computed
as `abs(wall - topbot) / max(wall, topbot)`. The field SHALL state both thickness values and
the percent difference. When the two are within 25% of each other, the field SHALL be
absent. Emitting this warning SHALL NOT change `status` or cause the advisor to skip or
block -- it is additional information within the same never-blocking result.

#### Scenario: Divergent thickness triggers a warning
- **WHEN** a profile's wall thickness and top/bottom shell thickness differ by more than
  25%
- **THEN** the result carries `thickness_mismatch_warning` stating both values and the
  percent difference, and `status` is unaffected

#### Scenario: Matching thickness emits no warning
- **WHEN** a profile's wall thickness and top/bottom shell thickness differ by 25% or less
- **THEN** the result carries no `thickness_mismatch_warning` field
