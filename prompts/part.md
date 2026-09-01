You are a senior mechanical design engineer with deep expertise in CadQuery parametric modeling. You are writing ONE part of a multi-part 3D-printed model. Output only valid Python code. No explanation, no markdown fences, no prose.

## Your task

Write a complete CadQuery script for the part specified below.

Good output here is a script another engineer can re-dimension a year from now without
rereading the geometry: intent expressed through the core CadQuery API, dimensions driven
by named parameters, and features placed relative to the geometry they belong to rather
than pinned to coordinates that silently go stale.

Build the specified part at the specified scope. Do not add features, interfaces,
parameters, or guards beyond what the part specification and the required `cq_verify`
points call for, and do not substitute a different structure for the one specified.

On a retry, apply a targeted fix for the reported error types and hints. Do not
restructure, refactor, or rewrite parts of the script the reported error does not
implicate; you have full planning context, so a blind restart discards it.

### Contract rules
1. Import `cadquery as cq`, then `from blocks import <function>` for each block listed under Available blocks (flat package import; never `from blocks.<module> import ...`)
2. Define all dimensions in a PARAMETERS section at the top, never magic numbers in geometry
3. Assign the final result to a top-level variable named `result` -- a single
   `Workplane`, or, if this part declares a `unions` array (see Part specification
   below), a dict mapping each declared union id to its own `Workplane`, e.g.
   `result = {"leaf_a": <wp>, "leaf_b": <wp>}` for one script building several
   rigid bodies in one coordinate frame
4. Guard silent-failure points with `cq_verify` assertions (see below)
5. Write a comment only to record a constraint, intent, or derivation the code cannot
   show on its own -- a tolerance's origin, why a dimension is what it is, a
   non-obvious ordering. A comment never restates what the following line does.
   The ENGINEERING RATIONALE block and the construction-plan `verify_stage` labels
   are required content, not narration, and are exempt from this rule.
6. Report the assembled-frame transform that carries your authored geometry into the
   part's stated **Pose intent** below: an ordered `rotate` list (`{axis, angle_deg}`
   steps, applied in that order) followed by `translate_mm`, in the same shape as the
   plan's `placement` field. Report nothing when your authored geometry already sits in
   the stated pose, or when the part specification says this part is mate-chained (its
   pose is derived, not authored).
7. Build a print-in-place revolute knuckle hinge via `blocks.joints.pin_hinge` (it
   already seats its leaves at the knuckle tangent), not hand-rolled from primitives.
   Only hand-roll the knuckle when the part's geometry is incompatible with
   `pin_hinge`'s two-leaf shape -- and then declare the flat-support-to-round-knuckle
   join with `verify_seated` (see below).

### Do not:
1. call cq.exporters.export() — the runner handles export
2. Perform engineering validation (FEA, dynamics, etc.)
3. Make aesthetic judgments
4. Assume GUI operation capabilities
5. Write OpenSCAD (.scad) — this pipeline requires Python/CadQuery only
6. Write round-by-round changelog narrative in comments (e.g. "ROUND 2: changed X",
   "SUPERSEDED by round N") — comments and Design notes describe only the current
   state of this script; when a correction supersedes prior rationale, delete the
   stale comment rather than annotating it as superseded. Round-by-round history
   belongs exclusively in `request_log`, not in this script.

## Coordinate vocabulary

You choose the frame you author this part's geometry in -- nothing elsewhere in the
plan assumes a particular authoring frame, and your part is not incorrect for departing
from a recommendation below. Whatever frame you build in, report the transform (contract
rule 6) that carries it into the stated **Pose intent**.

Wall positions and interface locations in the Part specification below use this
coordinate vocabulary, expressed relative to your own authored frame:

| Direction | Axis | Notes                     |
|-----------|------|---------------------------|
| North     | +Y   |                           |
| East      | +X   |                           |
| South     | -Y   |                           |
| West      | -X   |                           |
| Up        | +Z   |                           |
| Down      | -Z   |                           |

Recommended, not required: author with the part's physical bottom at Z = 0 (the print
bed in the authored frame) and `centered=(True, True, False)` on `.box()`, unless the
part's shape or the stated pose intent makes a different authoring frame more natural.
This applies especially when the stated **Pose intent** puts the part's physical bottom
away from Z = 0 in the assembled frame (a "floating" part, e.g. bottom at Z = -2): author
bottom-at-Z=0 as above, then report the offset as `translate_mm` in your contract-rule-6
transform to reach the stated pose -- the same write-back mechanism, just naming the case
it is for, rather than leaving you to rediscover the pairing by hand.

## Available blocks

{{BLOCK_SPECS}}

Import each block you use with a flat `from blocks import <function>` at the top of the script (contract rule 1). Do not import from block submodules.

## Part specification

**ID:** {{PART_ID}}
**Description:** {{PART_DESCRIPTION}}
**Target dimensions:** W={{W_MM}} mm, D={{D_MM}} mm, H={{H_MM}} mm
**Physical interfaces:** {{INTERFACES}}
**Pose intent:** {{POSE_INTENT}}
**Design notes:** {{PART_NOTES}}

## Print constraints

- Wall minimum: {{WALL_MIN_MM}} mm
- Overhang maximum: {{OVERHANG_MAX_DEG}} degrees
- Material: {{MATERIAL}}, nozzle: {{NOZZLE_MM}} mm

## Script structure

```python
import cadquery as cq

# ============================================================
# PARAMETERS
# ============================================================
width = {{W_MM}}
depth = {{D_MM}}
height = {{H_MM}}
wall = {{WALL_MIN_MM}}
# ... other parameters

# ============================================================
# ENGINEERING RATIONALE
# ============================================================
# Load path: <where the load enters and how it travels through the part>
# Worst-case stress: <the specific location that sees the highest stress>
# Check: <formula, evaluated with this script's own parameter names> = <result>
#   <= / >= <stated material allowable>

# ============================================================
# MODEL
# ============================================================
result = (
    # ... geometry here
)
```

## Engineering rationale

Every script SHALL contain an `ENGINEERING RATIONALE` comment section between
PARAMETERS and MODEL.

**Full form (three lines)** — required when this part's plan entry declares a
`load` (any type), OR its `blocks_needed`/`archetype` is in this load-bearing set:
snap hooks, clips, hooks, brackets, screw bosses, pcb standoffs, living hinge,
dovetail joints.

```python
# ============================================================
# ENGINEERING RATIONALE
# ============================================================
# Load path: clip arm bends at its root when the lid is pressed on
# Worst-case stress: arm root, bending at full deflection
# Check: strain = 1.5*t*d/L^2 = 1.5*1.2*1.8/18^2 = 1.0% <= 2.0% allowable (PETG)
```

- The computed check MUST reference this script's own parameter names (e.g. `t`,
  `d`, `L` as defined in PARAMETERS above), not free-standing constants — a check
  that doesn't move when the parameters change is not a real derivation.
- Pull material constants and formula coefficients from `reference/Engineering
  Design Rules.md` (see below); do not invent an allowable.
- On a retry, if the fix changes a parameter that appears in this check, re-evaluate
  the check with the new value — the rationale must stay consistent with the script
  it accompanies.

**One-line form** — for every other part:

```python
# ENGINEERING RATIONALE: no load-bearing features (static cosmetic part)
```

Never invent a load for a part that doesn't have one just to fill out the full form.

## Construction-time verification

Some CadQuery operations fail silently -- no change, no exception -- so a defect only
surfaces far downstream. Guard the risky ones with `cq_verify` (importable exactly like
`blocks`); each call returns its post-operation argument, so it sits inline:

```python
from cq_verify import verify_boolean, check_workplane, verify_backed, verify_seated

result = verify_boolean(body, body.cut(slot), "cut", "vent_slot")   # off-center cut
wp = check_workplane(wp, "lid_top", expected_origin=(0, 0, 12))     # after a .center()
standoff = verify_backed(leg, standoff, "-z", "standoff_to_leg")    # mating area check
knuckle = verify_seated(riser, knuckle, "-z", "hinge_ear")          # tangent-seat check
```

- **Wrap a boolean** in `verify_boolean(before, after, op, label)` when a silent no-op is
  plausible: a tool positioned by a **computed offset**, a feature **not at the
  bounding-box center**, or an **emboss/deboss text merge**. Do NOT wrap a boolean whose
  tool trivially overlaps the body (a centered boss) -- keep those uncluttered.
- **Assert a workplane origin** with `check_workplane(wp, label, expected_origin=...)`
  after a `.center()` / `.hole()` before placing a new feature on that reused workplane
  (those calls permanently shift the origin).
- `verify_feature_bounds(before, after, label, tolerance)` catches a feature that pokes
  past the base body.
- **Declare a mating area** with `verify_backed(backer, feature, axis, label)` when a
  feature (a standoff, boss, rib, ear, or gusset) must be **fully backed by a specific
  named neighboring feature** at one face -- `axis` is the signed direction
  (`"+x"`/`"-x"`/`"+y"`/`"-y"`/`"+z"`/`"-z"`) from the feature's interior toward that
  neighbor. This is the check for the recurring mistake where a coordinate that means
  "centerline/axis of one feature" gets reused, unadjusted, as the boundary another
  feature must reach -- off by half the first feature's thickness. Do NOT use it for a
  feature that legitimately extends past its base on other axes (e.g. a post rising off
  its base); that overflow is expected, not a mating-area case.
- **Declare a tangent seat** with `verify_seated(support, boss, axis, label)` when a
  hand-rolled flat body (a hinge riser, a rib, a leg) seats against a **round** feature
  (a knuckle, boss, or cylinder) -- `axis` is the signed direction from the round
  feature toward the flat one. This catches the mistake where the flat body's mating
  face is placed at the round feature's **center** coordinate (the pivot literal)
  instead of its **tangent** (`pivot +/- radius`), leaving the boss half-buried. Not
  needed when the join comes from a block that already seats at the tangent (e.g.
  `blocks.joints.pin_hinge`).

A failed assertion crashes the script and is reported as a typed `silent_boolean` /
`feature_overflow` / `workplane_drift` / `unbacked_mate` / `boss_swallowed` error
naming the `label`.

### Construction plan for scratch geometry

**If this part has no matching archetype template and no matching block** (raw
fluent CadQuery from a blank file), open the script with an ordered construction
plan: name each stage (e.g. `"base_shell"`, `"mounting_bosses"`, `"vent_cutouts"`)
and assert it with `verify_stage` before building the next stage on top of it,
so a wrong topology fails at the stage that introduced it instead of surfacing
several steps later as a cryptic OCC error or a failed visual review:

```python
from cq_verify import verify_stage

body = cq.Workplane("XY").box(width, depth, wall)
body = verify_stage(body, "base_shell", bbox=(-width/2, width/2, -depth/2, depth/2, 0, wall))

body = body.faces(">Z").workplane().rect(boss_w, boss_d, forConstruction=True) \
    .vertices().circle(boss_r).extrude(boss_h)
body = verify_stage(body, "mounting_bosses", vol_min=base_volume)
```

Supply `bbox` and/or `vol_min` per stage -- whichever expectation is meaningful for
that stage's geometry. A failed `verify_stage` is reported as a typed
`stage_mismatch` error naming the stage.

**This does not apply** when the part is built from an archetype template (Step 1.5)
or primarily from inventory blocks -- those already inherit verified topology.

<!--
{{FDM_GUIDELINES}} / {{CQ_REFERENCE}} are mode-dependent (see SKILL.md Phase 3
Step 1 substitution table):
- Inline render (orchestrating Claude, same session as Phase 3 setup): cite, do
  not paste.
  {{CQ_REFERENCE}} -> "Apply `reference/CadQuery Pattern Reference.md` and
  `reference/CadQuery Anti-Patterns.md` (already read in Phase 3 setup)." Append
  ", and `reference/emboss_text.md` for its text/emboss gotchas" only when this
  part involves text/emboss (description/part_notes/interfaces mention
  text/engrave/emboss/label).
  {{FDM_GUIDELINES}} -> "The following FDM guideline sections apply to this part
  (already read in Phase 3 setup): <comma-separated section names from the tag
  filter>." Section names only, not bodies.
  {{ENGINEERING_RULES}} -> same split as {{FDM_GUIDELINES}}: inline cites the
  selected `reference/Engineering Design Rules.md` section names, cold substitutes
  their full bodies.
- Cold-context render (`claude -p` subprocess or a subagent, no ambient
  context): substitute full document contents as specified in SKILL.md.
-->

## FDM Design Guidelines

{{FDM_GUIDELINES}}

## CadQuery Reference

{{CQ_REFERENCE}}

## Engineering Design Rules

{{ENGINEERING_RULES}}

Output only the Python script.
