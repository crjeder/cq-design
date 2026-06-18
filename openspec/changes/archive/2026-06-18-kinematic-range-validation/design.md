## Context

The part loop fuses each part to a single `result` Workplane and exports one STL
per part (deliver mode). The block inventory already tags joints with a `motion`
axis (`hinge` | `ball` | `rigid`) for selection, but there is no machine-readable
description of the joint's degree of freedom (axis, type, range) and no stage that
verifies motion. `quality_gate.py` already establishes the pattern this stage
follows: load exported STLs with trimesh, compute a geometric property, emit
structured `{source, severity, type, message, hint, ...}` issues, and degrade to a
`check_skipped` warning when a dependency is missing.

The user's driving example: a phone holder whose arm folds 90 degrees from
upright to flat. The design depends on that 90-degree range being collision-free.
The mechanical hinge could in principle reach ~180 degrees, but only 0..90 is
required, so the sweep is bounded to the declared range — not the full mechanical
range.

## Goals / Non-Goals

**Goals:**
- Verify a joint achieves its author-declared range of motion without collision.
- Keep the structure declared, not inferred: the author states axis and range in
  `BUILD_PLAN.json`; the block states its nominal DOF in the inventory.
- Stay in-process and deterministic (trimesh + fcl), matching the direction of the
  overhang-analysis change.
- Preserve the existing issue contract so downstream stages need no changes.

**Non-Goals:**
- Dynamics (gravity, torque, stability) — out of scope; kinematic only.
- Inferring the joint axis from block internals — explicitly rejected (see below).
- Print-in-place single-body joints and `living_hinge` — out of scope.
- Auto-suggesting a fix for a binding joint beyond reporting the binding value.

## Decisions

**Decision: required range subset-of mechanical limit, sweep is truth.**
Two checks per joint. (1) Declared-vs-declared: `required_range ⊆ mechanical_limit`
from the inventory — a cheap numeric sanity gate that catches "you asked for 270
degrees on a 180-degree hinge" without touching geometry. (2) Geometry sweep: step
the moving part through the required range and test collision against the fixed
part. The inventory `mechanical_limit` is *nominal* — it is the block's ideal full
range and is not adjusted for the instance's leaf thickness or wall. The sweep is
the authority on what the printed part actually clears. Rationale: a fixed nominal
keeps the inventory simple and stable, while the sweep captures the real,
parameter-dependent interference (thick leaves self-collide before 180 degrees).

**Decision: `mechanical_limit` + `unit`, not a `_deg` suffix.**
A revolute/spherical joint's range is in degrees; a prismatic joint's travel is in
millimetres. Encoding the unit in the field name (`mechanical_limit_deg`) is wrong
for prismatic. Use a neutral `mechanical_limit: [lo, hi]` plus an explicit
`unit: "deg" | "mm"`. The plan mirrors this with `required_range` + `unit`. The
checker asserts the plan `unit` matches the block `dof.unit` for the joint type.

**Decision: author declares the joint axis in the plan (`axis_origin_mm` +
`axis_dir`), not derived from block internals.**
The collision sweep needs a world-space pivot point and direction. Deriving it from
each block's construction (e.g. hinge axis at `(0, *, d_outer/2)` pre-transform)
would couple the checker to every block's internal geometry and to the part's
assembly transform. Declaring it in the plan keeps the checker geometry-agnostic
and consistent with the "declare, don't infer" choice for the rest of the
structure. `axis_dir` is one of `X`/`Y`/`Z` for v1 (axis-aligned joints); arbitrary
direction vectors are a possible later extension.

**Decision: trimesh + fcl collision sweep, not PyBullet.**
The job is "is the moving link collision-free at a sequence of transforms through a
bounded range." That is exactly `trimesh.collision.CollisionManager` with a
transform applied per step. PyBullet would require generating URDF from the
CadQuery parts to buy rigid-body dynamics that are out of scope. fcl is a far
lighter dependency than a full physics engine and keeps the stage deterministic
and offline. `python-fcl` must be added as a dependency; the stage degrades to a
`check_skipped` warning if it cannot be imported.

**Decision: bounded sweep over the required range, coarse step.**
Sweep only `required_range`, not `mechanical_limit`. Step granularity comes from
the plan's `step` (default a few degrees / a small mm increment). Always include
both endpoints. Report the first step at which collision is detected as the
binding value. A coarse step can miss a thin mid-arc interference; this is an
accepted v1 limitation, documented, and tunable via `step`.

**Decision: revolute transform.**
For a revolute joint, the per-step transform is a rotation by theta about the line
through `axis_origin_mm` in direction `axis_dir`, built with
`trimesh.transformations.rotation_matrix(angle, direction, point)`. Prismatic is a
translation of `d` along `axis_dir`. Spherical is deferred in the sweep to a cone
sampling around `axis_dir` up to the required cone half-angle (v1 may check only
the cone boundary; flagged as a known coarseness).

## Risks / Trade-offs

- **Coarse-step miss**: a sweep at 5-degree steps can step over a 2-degree-wide
  interference. Mitigation: endpoints always tested; `step` is author-tunable;
  documented limitation.
- **Spherical fidelity**: cone sampling is an approximation of a true spherical
  workspace. v1 scopes this down (boundary sampling) and documents it.
- **Axis correctness is on the author**: a wrong `axis_origin_mm` produces a
  meaningless sweep. The checker cannot validate the axis against geometry without
  the coupling we rejected; a clearly-wrong axis tends to surface as immediate
  collision at step 0, which the finding reports.

## Migration

- `dof` on inventory entries and `kinematics` on the plan are both additive and
  optional. Existing plans without `kinematics` skip the stage entirely; existing
  inventory entries without `dof` are unaffected (only joints referenced by a
  `kinematics` entry need `dof`).
