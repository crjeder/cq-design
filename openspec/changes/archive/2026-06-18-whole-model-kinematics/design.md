# Design notes

## The conflation this change removes

A "part" today is simultaneously a rigid body and a print job. These are
independent groupings:

```
                  SAME PLATE?  (print job: fusion / clearance)
                  ┌─────────────────────┬─────────────────────┐
                  │        YES           │         NO          │
   ┌──────────────┼─────────────────────┼─────────────────────┤
 CHECK   YES      │ print-in-place hinge │ box + separate lid  │
TOGETHER (assemble│ 2 unions, 1 plate    │ 2 unions, 2 plates  │
  ?      /move)   │ fuse(STL)/lock(3MF), │ separate objects,   │
                  │ check the 2 unions   │ check the 2 unions  │
   ┌──────────────┼─────────────────────┼─────────────────────┤
         NO       │ trinkets batched     │ unrelated parts     │
                  │ on one plate         │                     │
   └──────────────┴─────────────────────┴─────────────────────┘
```

The checker is **plate-blind**: it always operates on per-union assembled meshes.
Plate membership only affects export (fusion/locking) and the future clearance
gate. "Checked together" (assembly) and "printed together" (plate) are orthogonal,
so they are separate fields, or the common box-on-two-plates case is
unrepresentable.

## Three poses

```
MODEL pose = block authored frame  ×  planner placement     (arbitrary)
USE  pose  = articulated state; sweep runs here, v relative to required_range[0]
PRINT pose = chosen downstream by mesh analysis (strength/support)  -> ignored by check
```

Decision: **blocks are authored in use pose**; `dof` ranges and `interfaces` are in
that frame. The sweep zero is the authored use pose. This retires the prior
ambiguity (was `v` measured from flat or closed?). The check runs in assembled/use
coordinates; the per-union mesh fed to it must therefore be in assembled pose, not
plate pose -- which is why the assembled 3MF (not the print layout) is the source of
truth.

## Export: assembled 3MF as source of truth

- One 3MF, each union a separately named object carrying its assembled-pose
  transform and a `plate` tag (metadata). Operator re-distributes objects to plates.
- Print-in-place: co-plated unions marked as a locked cluster (relative transform
  fixed; operator may move the cluster, not separate it).
- No boolean fusion in 3MF -- named objects preserve identity natively.
- STL fallback: per-union STL (for checking / single-object consumers) plus one
  fused STL per plate (STL cannot carry multiple objects in fixed relative pose).
- The kinematic check reads per-union assembled meshes from the 3MF.

## Decision: structured placement is the source of truth for assembled pose

Discovered at apply time: the pipeline had no structured assembled-pose data. Parts
are authored in their own local frames and the freeform assembly script baked
positions into a single fused blob, so neither the whole-model sweep nor a named
3MF could recover per-union poses. Resolution (chosen by the user):

- Each union carries an optional `placement` mapping its local frame into the shared
  assembled frame: `{ translate_mm: [x,y,z], rotate: [{axis: X|Y|Z, angle_deg}, ...] }`.
  Absent = identity (union authored directly in the assembled frame). Rotations apply
  in listed order, then translation, matching CadQuery `.rotate()`/`.translate()` and
  a composed 4x4 for trimesh / 3MF.
- A new model-level export (`src/model_export.py`) loads each union's `result`,
  applies its placement, and emits: (a) one 3MF with each union as a named object
  carrying its placement transform + `plate` metadata; (b) one assembled-pose STL per
  union (checker input / single-object consumers); (c) one fused STL per plate that
  holds more than one union.
- The kinematic check positions each union by its placement, then sweeps.

Assembly-phase reconciliation: structured `placement` supersedes the freeform
assembly script for *positioning*. Boolean clearance cuts between mating parts are
out of scope for this change (clearances stay handled per-part as today); the fused
deliverable is the per-plate fused STL from the model export.

## Decision: hand-declared unions in v1, docks later

The check only *needs* per-union meshes + axis + range, all declarable in the plan.
Side-tagged `face_mount` docks would let the planner *derive* union membership and
the world axis (and validate "leaf not unioned to anything" / "both leaves in one
union = rigid"), but that is a larger block-API change. v1 hand-declares; dock
derivation is a follow-up.

Naming caveat (raised in exploration): the block `interfaces` array already mixes
two roles -- assembly/mating docks (`face_mount`, what the *planner* attaches user
geometry to) and kinematic axes (`hinge_axis`). Technically both are connection
interfaces, but conflating them invites misconception. Keep them distinguished by
`type` and, in docs, by role (dock vs axis) even though they share the array.

## Resolved decisions

- **Fixed set = separate collision objects, not a combined mesh.** The kinematic
  check runs inside a design loop where the LLM must fix the binding, so it needs to
  know *which* union collided, not merely that one did. Each non-moving union is
  added as its own named collision object, and `motion_collision` reports the
  colliding union id (alongside the binding value).
- **`required_range` is relative to the authored pose, with the authored pose as
  zero.** The range may be negative and straddle zero, e.g. `]-30, 90]`. Bound
  inclusivity follows mathematical interval notation: in `]-30, 90]` the lower bound
  is **open** (-30 need not be reached) and the upper bound is **closed** (90 must be
  cleared). The sweep always includes a closed bound and may exclude an open bound; a
  collision counts only when it falls within the (possibly half-open) required
  interval, so an excluded endpoint never produces a false positive that would waste
  a design-loop iteration. The schema must therefore carry per-bound inclusivity, not
  just two numbers (exact JSON encoding decided at apply time -- e.g. `[lo, hi]` plus
  `lo_inclusive` / `hi_inclusive`, default closed/closed).

## Open questions

(none outstanding)
