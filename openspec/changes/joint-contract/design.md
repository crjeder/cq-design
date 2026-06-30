# Design: joint-contract (exploratory capture)

> Captured from an explore session. This is the *thinking*, with open cruxes marked. It is not a
> committed design; `tasks.md` stays blocked until the remaining crux (satisfaction algebra for
> spherical) resolves.
>
> **Status update (2026-06-30 explore session):**
> - **Crux 2 (sub-body naming) -- SHIPPED.** Option 3 landed on `main` via the `multi-union-parts`
>   change: `src/units.py` (`iter_unions`/`resolve_unions`) is the "union is a first-class plan
>   entity" mechanism -- the plan declares `unions`, the script returns a `name -> Workplane` dict,
>   `model_export` splits per key, `kinematics.moving_union` is a union id, N=1 is byte-identical to
>   today. The keystone this whole design "rides on" is in.
> - **Topology -- DECIDED: Topology 1.** Each joint is owned by ONE block that emits both sides as a
>   multi-union dict (see "Topology decision" below). This deletes the A/B-binding sub-problem of
>   crux 1.
> - **dof datum -- DECIDED: authored pose.** Limits are read from the pose the block is drawn in;
>   revolute needs NO angular reference vector (see "dof vector model" below).
> - **Crux 1 (satisfaction algebra) -- single-axis (revolute + prismatic) is now tractable; spherical
>   (ball joint) is the one open fork.**

## The core reframe: dof is a contract

A joint is a relation between two unions `A` and `B`. The relation is **symmetric** -- roles are
arbitrary; the kinematic solver decides which body to hold fixed and which to sweep, since only the
*relative* motion is physical. Both sides speak the same vocabulary:

```
   PLAN = the WISH                         BLOCK = the REALITY
   "what the model needs"                  "what's in the LEGO box"
   need: rotate(A↔B), Z, [0,90]            pin_hinge: rotate(leafA↔leafB), Z, [0,180]
            └────────────── SATISFIES? (wish ⊆ reality) ──────────────┘
   today plan_validate checks only unit==; it never checks type, so a revolute
   wish against a ball_socket block passes. The contract closes that hole.
```

## The joint shape

```
joint = {
  between: ["A", "B"]                 # two unions; symmetric; solver picks the pinned one
  movements: [                        # LIST — independent for now (coupling = TODO)
    { motion:    "rotate",            # rotate | translate   (unit DERIVED, not stored)
      axis:      [0,0,1],             # the line / direction
      reference: [1,0,0],             # rotate: ⟂ axis, marks 0° (12 o'clock) + sign
      range:     [0,180] }            # translate: `reference` is the 0 POSITION instead
  ]
}
```

- **`unit` dropped** -- `rotate` ⇒ deg, `translate` ⇒ mm is derivable.
- **`reference` vector.** One vector suffices for a single axis but means different things by
  motion: for `rotate` it is perpendicular to the axis and fixes the 0° direction (with the axis
  and right-hand rule it also fixes sign); for `translate` it is the zero position on the line.
- **Spherical is not a fourth type** -- it is two coupled `rotate` movements sharing a center.
  Listing two *independent* entries models a 2-axis gimbal, not the ball's *coupled* cone; a single
  `reference` cannot pin a sphere (it needs a frame). True coupling (also helical screw pitch) is
  the multi-DOF TODO.
- **Plan range vs block range.** Block `range` is the nominal full travel (reality); plan `range`
  is what the design requires (wish), relative to the authored pose. Keep the distinction.

## Block ≠ union (the enabling decoupling)

```
   TODAY                                YOUR MODEL
   block ─1:1─ body ─1:1─ union         block ─1:N─ unions
   joint fragmented across two           joint OWNED by one block (both members
   independent parts; dof knowledge      + the dof relating them); PLAN binds
   re-asserted by hand in kinematics     each member → a union
```

The **union stays the atom** of "rigid printed body" -- the sweep, plate-clearance, and per-object
export all still operate per union. Only the one-block-one-body assumption is relaxed. A block that
emits two leaves is still two unions; they remain independently printable, even on different plates.

### Keystone (crux 2, OPEN): naming sub-bodies

A CadQuery `result` can already be a compound of several disjoint solids. The wall is that
`model_export` collapses one part into one union:

```
   model_export:  for part in parts:
                    wp = _load_result(script)        # one result
                    makeCompound(wp.vals())          # ALL solids → ONE named object = ONE union
```

So the sweep sees two leaves as one frozen blob. What's missing is a **name on each sub-body**:

```
   OUTPUT side: 3MF named <object>s — EXISTS (model_export already names per-union objects)
   INPUT side:  no native "name this solid" in a CadQuery compound — needs a CONVENTION:
                • block returns {union_name: Workplane}, or
                • the plan declares which unions a part contains, or
                • solids carry tags the exporter splits on
```

This one decision is the keystone -- multi-union blocks, derived kinematics, and chains all ride on
it. Pipeline note (per the session): the top-level script emits one `result`; it may import block
scripts that emit several bodies. The heavy machinery (export, kinematic, plate) runs at the END on
the arranged world.

### Options considered

The linchpin today: `union id == part id == script name` -- the single string used as the 3MF
object name, the `<id>.stl` filename, `kinematics.moving_union`, and the plate-grouping key. So
"name a sub-body" really means "break the union-id = part-id identity and give the plan a union
namespace to reference."

| | 1 Named-map result | 2 Auto-split by geometry | 3 Plan-declared + tagged | 4 Block-macro → N parts |
|---|---|---|---|---|
| union name owned by | script author | nobody (anonymous index) | **plan** (script fulfils) | planner (generated part ids) |
| joint built in one frame? | yes | yes | yes | no (split scripts, re-united by placement) |
| stable referenceable names? | yes | no (index reorders) | yes | yes |
| blast radius | wide | narrow (export only) | wide | none downstream |
| fatal flaw | invasive | disjoint != separate-union (over/under-splits) | invasive | loses "one block owns the joint" |

Option 2 is out as a primary mechanism (disjointness is a heuristic, not a definition). Options 1
and 3 are the same idea (script returns a `name -> geometry` map) differing in where the canonical
name list lives; since kinematics and plate must reference union ids from the plan anyway, 3 is "1
done properly." Option 4 is the low-risk escape hatch that contradicts the self-contained-joint goal.

### DECISION (crux 2 / D2): Option 3 -- union is a first-class plan entity

`union` becomes a first-class entity distinct from `part`/`script`. A build unit (script) yields
1..N unions; the PLAN names them and the SCRIPT binds geometry to each name. `union id = part id`
is the N=1 default (backward compatible).

```
 PLAN (wish names the unions)                  SCRIPT (reality fills them)
 { "id": "hinge",                              result = {              # dict, not one
   "unions": ["leafA","leafB"],   NEW            "leafA": wp_a,        # Workplane. keys
   "blocks_needed": ["pin_hinge"] }              "leafB": wp_b }       # MUST match plan unions
 plate moves to the UNION level                backward compat:
   leafA -> plate p1, leafB -> p2                 result = wp -> one union, id = part id

 kinematics.moving_union: "leafA"   (a union id; sub-union now allowed)

 model_export: iterate UNIONS, not parts
   if dict: one named 3MF object + <uid>.stl per key
   else:    today's makeCompound path (id = part id)
   cross-check: dict keys == plan-declared unions     (new well-formedness check)
```

Blast radius lands in: **plan schema** (`unions` field; plate moves part->union), **the result
contract** (`_load_result` / `run_model_shim` / `run_cadquery_model` accept a `name->Workplane`
dict), and **`model_export`** (iterate + split + cross-check). The kinematic and plate stages barely
change -- they already key off per-union `<id>.stl` and a plate-grouping key; the id just becomes a
union id, and N=1 is byte-identical to today.

## Topology decision (D3): one block owns both sides of the joint

DECIDED: **Topology 1.** Every joint is owned by a single block that emits *both* members as a
multi-union result, and carries the `dof` relating them. This is the natural consumer of the shipped
crux-2 machinery: a joint block `return`s `{sideA: wp, sideB: wp}`, which is exactly
`resolve_unions`' dict path.

The inventory ships joints as single-body *halves* today; Topology 1 fuses each pair into one block:

```
 TODAY (halves, one Workplane, unions=None)   TOPOLOGY 1 (one block, multi-union)
 ──────────────────────────────────────────   ───────────────────────────────────────────
 dovetail_groove + dovetail_tongue          → one block → {groove, tongue}   prismatic
 ball_socket     + ball_stud                → one block → {socket, stud}      spherical (parked)
 hinge_leaf (×2) / pin_hinge                → one block → {leafA, leafB}      revolute
 living_hinge (dof-less flexure)              unchanged: single body, no dof
```

Why this and not Topology 2 (two half-blocks paired by the plan): with the joint owned by one block,
the block knows its own two sides, so the dof references its own (local) union names and the plan
only maps them to plan union ids. The hardest part of crux 1 under Topology 2 -- "whose dof is
canonical, and how do two independent half-dofs compose" -- simply does not arise.

## dof vector model (D4): two/three vectors in block coordinates, datum = authored pose

DECIDED. A `dof` carries its geometry as vectors in **block coordinates**; the assembled-frame axis
is derived by pushing them through the union's `placement`. `unit` is dropped (derived from `type`).

```
 prismatic: { type, direction, limit, between }            # limit mm
 revolute:  { type, origin, direction, limit, between }    # limit deg
   origin    = a point ON the axis (locates the axis line in space; the pivot)
   direction = slide direction (prismatic) | rotation axis (revolute); RHR about it fixes sign
   limit     = [lo, hi], measured from the AUTHORED POSE (how the block is drawn); may be
               negative / straddle zero -- the same convention kinematic_check already uses
   between   = the two unions this dof relates (the block's own sub-bodies)
```

**No angular reference (12-o'clock) vector is stored.** The reference's only job is to fix where 0
is; sign is already fixed by `direction` + right-hand rule, and the zero is supplied for free by the
pose the block is authored in. The asymmetry between the two motions is *not* an extra angular datum
for rotation -- it is that a **rotation axis must be located in space (the `origin` pivot) while a
translation direction need not be**. For translation one point would serve as both "point on the
line" and "zero of distance"; for rotation those split (the pivot is a point, the angular zero is a
direction), and the angular zero comes from the authored geometry rather than a stored vector.

Price (accepted): the block author draws the block at the pose they call zero and states limits
relative to it. A stored `reference` would only be needed to decouple 0 from the authored geometry
(absolute hard-stops, absolute-angle reporting) or for coupled/spherical joints (parked).

## Annotation geometry: printed vs pseudo

The model needs a classification it lacks today:

```
   BLOCK-DECLARED INTENT                          printed?  swept?  checked?
   1. JOINT CONTRACT    what MOVES (A↔B, moves[])    —        ✓        ✓
   2. MATING AREA       WHERE to connect (2D)         ✓        —        ✓   keep-out
   3. ASSEMBLY ENVELOPE keep-CLEAR-to-assemble (3D)   ✗        ✗        ✓   pseudo
```

- **printed** geometry is exported and swept.
- **pseudo** geometry is invisible to export and the sweep but live for intent checks.

### Mating area (2D footprint)

A block declares where it connects as a 2D area (e.g. a rectangle `[pA, pB, pC, pD]`), not just a
point + direction like today's interface. Purpose: *primarily* guide the LLM to use the block
correctly; *also* a gate check. Two rules:

- **Backed by material:** a mate area MUST be touched by a *to-print* object in its **own union**
  (the same rigid body) -- the connection surface is realized by real material, not floating.
- **Keep-out:** unrelated geometry must not intrude on the mate area, or it defies the part's intent.

### Assembly envelope (3D pseudo-volume)

A block may declare the volume that must stay clear to *assemble* it (a hinge's pin-insertion path,
the leaf swing during assembly). It is exempt from export (not printed) and from the sweep (not a
moving body), but printed geometry must not intrude on it or assembly is blocked. It is the 3D
keep-clear twin of the 2D mate-area keep-out, and is distinct from the model's own running-clearance
gaps.

## Target pipeline ordering

```
   design loop arranges the world (one result, named sub-bodies)
        │
        ▼
   kinematic solver validates IN PLACE on the arrangement
        │  (closes the export→read-STL chicken-and-egg of today)
        ▼
   model_export serializes the deliverable AFTER validation
```

Differs from today, where `model_export` runs first to produce the assembled-pose STLs the kinematic
check consumes. Target: solve on live geometry, export the deliverable only once it validates.

## Gate additions implied

- **Contract satisfaction** (replaces the lone `unit==` check): motion/axis/range match; closes the
  revolute-vs-ball_socket gap.
- **Mate-area checks:** backed-by-own-union-material, and foreign keep-out.
- **Assembly-envelope check:** no printed geometry intrudes on a declared keep-clear volume.

## Cruxes

1. **Satisfaction algebra (crux 1).** Now largely resolved for single-axis joints by the Topology-1
   and dof-vector decisions:
   - **A/B binding -- RESOLVED.** Topology 1 makes the joint block own both sides; the dof's
     `between` names the block's own unions and the plan maps them. No cross-block composition.
   - **Axis match -- direction set.** Push the block-frame `dof` vectors through the union's
     `placement`, then compare to the plan wish: revolute requires *coaxial* (same line: origin +
     direction), prismatic requires *parallel* (direction only -- sliding along any parallel line is
     the same motion). (Exact tolerance/normalization still to spec.)
   - **Range subset -- datum set.** Both block range (reality) and plan range (wish) are measured
     from the authored pose; satisfaction is `wish ⊆ reality` directly. (Exact inclusivity rules
     still to spec.)
   - **Spherical / ball joint -- PARKED (option a).** The single-axis `{origin, direction, limit}`
     model cannot express a cone (needs `{center, cone_axis, half_angle}`). Decision: the ball
     carries no contract dof for now; its mate stays a geometry-only check, and spherical joins the
     coupled-multi-DOF TODO. The satisfaction algebra ships covering revolute + prismatic only -- one
     coherent single-axis rule. (Inventory consequence: `ball_socket`/`ball_stud` are still fused
     into one block under Topology 1, but that block declares no `dof` yet.)
2. **Sub-body naming convention (crux 2, SHIPPED).** Option 3 landed on `main` via `multi-union-parts`
   (`src/units.py`). Union is a first-class plan entity; the plan names the unions, the script returns
   a `name -> Workplane` map. See the status note at the top.
3. **Topology (D3, RESOLVED -> Topology 1)** and **dof vector model (D4, RESOLVED -> authored-pose
   datum, no angular reference).** See the two decision sections above.
