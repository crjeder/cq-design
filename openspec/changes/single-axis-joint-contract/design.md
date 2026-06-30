# Design: single-axis-joint-contract

## Context

Today `plan_validate._check_kinematics` does one cross-check on a joint: `entry["unit"] !=
dof["unit"]`. It never checks joint `type`, axis, or range, so a `revolute` wish against a
`ball_socket` block, or a hinge declared about the wrong axis, validates. The block's `dof` is
`{type, axis (an "X"/"Y"/"Z" string), mechanical_limit [lo,hi], unit}`; the plan's `kinematics`
entry separately declares the assembled-frame `axis_origin_mm`, `axis_dir` ("X"/"Y"/"Z"), `type`,
`required_range`, `unit`, `step`.

Two facts shape the design:
- `src/placement.py` already turns a part's `placement` (ordered X/Y/Z rotations + translation) into
  a transform; the block's `dof` vectors live in **block coordinates** and must be pushed into the
  assembled frame to be compared with the plan's assembled-frame wish.
- `src/plan_validate.py` currently imports only stdlib + `jsonschema`; `tests/test_plan_validate.py`
  runs sub-second with no CadQuery and no heavy numeric stack. Keeping that path light is a
  constraint.

This is the first shippable slice of the parked `joint-contract` exploration. The dof vector model
(D4) and the satisfaction-algebra decisions (axis match, range datum) were settled there; this
design applies them to the existing block topology.

## Goals / Non-Goals

**Goals:**
- Replace the `unit==`-only check with a real satisfaction check (type + axis + range) for
  `revolute` and `prismatic` joints.
- Reshape `dof` to the block-coordinate vector model so the axis can be validated across `placement`.
- Keep the plan-validate path free of CadQuery and the trimesh/fcl stack.

**Non-Goals:**
- Topology-1 block merge (one block owning both joint members as multi-union bodies).
- Spherical/ball contract checking (parked; ball keeps an unchecked `dof`).
- Derived kinematics -- dropping the plan's now-partly-redundant `axis_dir`/`axis_origin_mm`. This
  slice cross-validates them against the block instead of deriving them away.

## Decisions

### D1: dof is a block-coordinate vector model; unit derived; datum = authored pose

```
 prismatic: { type, direction, mechanical_limit }            # mm
 revolute:  { type, origin, direction, mechanical_limit }    # deg
   direction        = slide direction (prismatic) | rotation axis (revolute), block coords; RHR fixes sign
   origin           = a point ON the axis (revolute only; the pivot), block coords
   mechanical_limit = [lo, hi] nominal full range; required_range (authored-pose-relative) must fall in it
```

`unit` is derived (`deg` for revolute, `mm` for prismatic), so the old `unit` field and the old
`axis` ("X"/"Y"/"Z") string are removed. **`type` and `mechanical_limit` are kept unchanged** -- the
substantive reshape is axis-string -> vectors plus dropping the redundant `unit`; the range field
and its existing semantics are left alone to keep the blast radius off the sweep and range-check
requirements. No angular reference vector is stored: sign comes from `direction` + right-hand rule,
the zero is the block's authored pose (already mandated by `printable-unit-model`, "Blocks are
authored in their use pose"). Full rationale incl. the "why no 12-o'clock reference" argument is in
`openspec/changes/joint-contract/design.md` (D4).

*Alternative considered:* keep `axis` as an enum string and skip vectors. Rejected -- a block axis
authored as "Y" can point any direction in the assembled frame after `placement` rotations, so a
string can neither be transformed nor compared correctly. Vectors are required for a correct axis
check.

### D2: satisfaction algebra = type ∧ axis ∧ range, axis compared in the assembled frame

For each `kinematics` entry whose `type` is `revolute` or `prismatic`:

1. **Type.** `entry.type == block.dof.type`, else a `joint_contract` error (this alone closes the
   revolute-vs-ball_socket hole).
2. **Axis.** Transform the block-frame `dof.direction` (and, for revolute, `dof.origin`) by the
   moving union's `placement` into the assembled frame, then compare to the plan's wish
   (`axis_dir`, and `axis_origin_mm` for revolute):
   - `revolute` -> **coaxial**: directions parallel (up to sign) AND the plan's pivot lies on the
     transformed axis line.
   - `prismatic` -> **parallel**: directions parallel (up to sign); position is irrelevant (sliding
     along any parallel line is the same motion), so `axis_origin_mm` is not constrained.
3. **Range.** Unchanged: the existing "required range within `mechanical_limit`" numeric check is
   the range arm of the contract and is reused as-is. Type and axis are the new arms.

Comparisons use an epsilon tolerance (parallelism via normalized dot product near ±1; point-on-line
via perpendicular distance below epsilon).

### D3: do the transform with a numpy-free helper, not `placement.to_matrix`

`placement.to_matrix` pulls in `trimesh.transformations`; importing it into the plan-validate path
would weigh down the fast, CadQuery-free test path. A `placement` is only ordered rotations about
`X`/`Y`/`Z` by `angle_deg` plus a translation, so the slice adds a small pure-Python helper that
rotates a vector/point through those steps (sin/cos, no numpy or trimesh). `placement.py` stays the
source of truth for the CadQuery/trimesh transforms; this is its lightweight twin for symbolic axis
math.

*Alternative considered:* import `numpy` only (lighter than trimesh). Acceptable, but pure-Python
keeps the validate path's dependency surface exactly as it is today (stdlib + jsonschema).

### D4: spherical is skipped, not errored

The check applies to `revolute` and `prismatic`. A `spherical` joint produces no `joint_contract`
finding (the cone model is parked); ball blocks keep their existing `dof` untouched so nothing
regresses. A comment/doc note marks spherical as intentionally unchecked.

### D5: migrate every `dof` consumer in lockstep with the reshape

Dropping `dof.axis`/`dof.unit` is BREAKING. `src/kinematic_check.py` keeps reading
`dof["mechanical_limit"]` (unchanged) but reads `dof.get("unit")` today; that one read is migrated to
a unit derived from `dof.type` in the same change so the sweep stage's numeric pre-check keeps
working. The inventory's revolute/prismatic blocks gain `direction` (+ revolute `origin`) and lose
`axis`/`unit`; ball blocks lose `axis`/`unit` too but stay `spherical` and unchecked.

## Risks / Trade-offs

- **Plan keeps two sources for the assembled axis** (`dof ∘ placement` vs the plan's `axis_dir`/
  `axis_origin_mm`). -> This is intentional for this slice: the contract check's whole job is to
  catch divergence between them. Collapsing to a single derived axis is the later derived-kinematics
  slice.
- **Floating-point axis comparison.** -> Fixed epsilon on normalized dot product and
  point-to-line distance; document the tolerance in the spec.
- **BREAKING dof reshape could silently skip checks if a consumer is missed.** -> D5 enumerates the
  consumers (`kinematic_check.py`, inventory, both schemas); tests assert the new error fires and
  that a migrated inventory still validates.
- **Pure-Python transform could drift from `placement.to_matrix`.** -> A test rotates a known axis
  through a non-trivial placement and asserts the helper agrees with `placement.to_matrix` (the test
  may import trimesh; the production validate path does not).

## Migration Plan

1. Reshape the `dof` schema in `inventory_schema.json` (drop `axis`/`unit`, add `direction` + revolute
   `origin`, keep `type`/`mechanical_limit`) and migrate `inventory.json` entries.
2. Migrate `kinematic_check.py`'s `dof.get("unit")` read to a unit derived from `dof.type`.
3. Add the satisfaction check (+ pure-Python transform helper) to `plan_validate.py`; drop
   `kinematics[].unit` from `build_plan_schema.json`.
4. Update fixtures/tests.

No runtime rollback concern (validation-only, no persisted artifacts). Rollback = revert the change.

## Open Questions

- Exact epsilon values for parallelism and point-on-line (pick during implementation; expose as
  module constants).
- Whether `required_range` subset uses inclusive or exclusive bounds at the limit edges (lean
  inclusive, matching the existing numeric check's behavior).
