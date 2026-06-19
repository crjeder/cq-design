## Why

The kinematic stage added in `2026-06-18-kinematic-range-validation` answers the
wrong question. It sweeps the two parts *of a joint* against each other -- it asks
"can this hinge open?" The interesting question is whether the joint clears its
range **inside the finished object**: a lid hinge might open 270 degrees in
isolation, but the box body blocks it at 180, or it fouls the floor at 210. The
hinge's nominal `dof` is a sanity bound; the assembled geometry is the truth.

The stage also special-cases print-in-place joints (`pin_hinge`, print-in-place
`hinge_leaf`) as "single fused body, no separate mesh to collide" and defers them.
That special case dissolves once the right abstraction is in place: a print-in-place
hinge is simply **two rigid bodies that happen to print on one plate**.

The root cause is that the pipeline conflates two independent groupings into one
"part":

- a **union** -- one rigid body, the unit of motion (kinematic subject), and
- a **plate** -- one print job, the unit of fabrication (fusion / clearance).

For ordinary parts these coincide, so it was never noticed. Print-in-place is
exactly where they must diverge. Separating them makes the kinematic check
whole-model, retires the print-in-place special case, and fixes the export model.

## What Changes

- **New planning concept: union vs plate.** A *union* is one rigid body (one
  kinematic subject; in this codebase a *part* is a union). A *plate* is a set of
  unions printed in one job. Default is one union per plate; a print-in-place
  mechanism is several unions tagged to one plate. The build plan gains a per-union
  `plate` tag. "The whole model is one assembly" -- the kinematic fixed set is
  *every other union*, not an enumerated pair (no `assembly` grouping field).
- **Structured assembly placement (new foundation).** Each union gains an optional
  `placement` (translation + rotations) giving its pose in the shared assembled
  frame; absent placement means identity (the union is authored already in the
  assembled frame). This is the single structured source of truth for where each
  union sits. The model-level export and the kinematic check both consume
  placements; parts are still authored in their own local frames.
- **Whole-model kinematic sweep.** A `kinematics` entry now names a *moving union*;
  the fixed set is derived as all other unions in the model. The sweep moves the
  union through `required_range` against the union of all fixed unions, in the
  **assembled (use) pose**, never the print pose. This catches in-context binding
  (lid vs box body) the joint-pair sweep cannot see.
- **Three poses made explicit.** Blocks are authored in their **use pose**;
  `dof` ranges and `interfaces` are expressed in that frame. The **model pose** is
  the block's frame times the planner's placement. The **print pose** is decided
  downstream by mesh analysis and is irrelevant to the check. The sweep zero is the
  block's authored use pose, retiring the old "model flat vs closed" ambiguity.
- **Export model: assembled 3MF as source of truth.** Export every union as a
  separately named object in one 3MF, each carrying its assembled-pose transform
  and `plate` tag as metadata (the operator re-distributes objects to plates).
  Co-plated print-in-place unions are marked as a locked cluster. The kinematic
  check reads per-union assembled meshes straight from this 3MF. STL stays a
  single-body fallback: per-union STLs for checking, plus a fused-per-plate STL for
  STL-only consumers.
- **`pin_hinge` stops being special.** It is two leaf-unions on a shared plate;
  kinematically identical to a pinned hinge. The only difference (no printed axle)
  is a plate/clearance note, never a kinematic one.

## Capabilities

### New Capabilities
- `printable-unit-model`: the build plan distinguishes *unions* (rigid bodies,
  kinematic subjects) from *plates* (print groups), with the whole model treated as
  one assembly and three explicit poses (use / model / print).
- `model-export`: unions are exported as separately named objects in an assembled
  3MF (source of truth for downstream checks and plate re-distribution), with a
  single-body STL fallback.

### Modified Capabilities
- `kinematic-range-validation`: the sweep subject is a *moving union* checked
  against every other union in the assembled model (whole-model collision), in the
  use pose; print-in-place single-plate joints are validated via their per-union
  meshes instead of being deferred.

## Impact

- **Code**: `src/build_plan_schema.json` (union `plate` tag, per-union `placement`,
  `kinematics` references a moving union + derived fixed set, signed/half-open
  `required_range`); `src/plan_validate.py` (union/plate/placement cross-checks);
  new `src/model_export.py` (model-level export: applies placements, emits named
  3MF objects + per-union assembled STL + fused-per-plate STL); `src/exporters/`
  (multi-object 3MF writer); `src/kinematic_check.py` (moving union vs all other
  unions as separate colliding objects, placements applied, signed/half-open range).
- **Inventory**: `pin_hinge` no longer needs separate kinematic treatment.
- **Docs**: `SKILL.md` (union/plate planning, assembled-3MF export, whole-model
  sweep), `CLAUDE.md` (export + kinematic notes), `prompts/planning.md` (emit unions
  and plate tags).
- **Tests**: whole-model sweep (lid blocked by box body), print-in-place two-union
  one-plate sweep, 3MF named-object round-trip, plate-tag validation.

## Out of Scope

- **Ground / seating plane** ("lid hits the floor"). No surrounding-geometry
  reasoning in this change; those questions belong to external simulation. Adding
  one simple ground plane is a tracked follow-up (`TODO.md`).
- **Articulated chains** (a moving union that carries other unions through the
  sweep). v1 is single-DOF: the mover is exactly one union. Tracked follow-up.
- **Plate clearance gate** (co-plated unions must keep gap > layer height or they
  fuse). Tracked follow-up.
- **Dock-driven derivation.** Auto-deriving union membership and the world joint
  axis from side-tagged `face_mount` docks is a follow-up; v1 hand-declares the
  moving union, axis origin, and axis direction in the plan. See `design.md`.
- **Dynamics** (gravity, torque, stability). The stage stays purely kinematic.
