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
> - **Topology -- DECIDED: Topology 1, on the matched-pair rationale.** One block is the single
>   source of a matched pair (A mates B iff same params); it emits both members as a multi-union dict
>   (see "Topology decision (D3)"). Applies to all mating pairs (hinge, dovetail, ball), NOT just the
>   print-in-place ones -- manufacturing is irrelevant. The lone-half `hinge_leaf` is retired.
> - **Composition + binding -- DECIDED: Option B (D6).** A joint's two members are `union`s fused
>   into parent parts, possibly DIFFERENT parts; a plan-level `joint` entity binds the pair to its one
>   parametric source so a mismatched pair is machine-caught. This is where the A/B binding actually
>   lives -- it is only trivial when both members land in the same part; across parts it needs D6.
> - **Mate model -- DECIDED (D6 refinements, see below).** Params live in a shared `parameters.py`
>   (single source, no drift). Fusion is in the ASSEMBLED frame (author assembly-pose-first; print
>   orientation is downstream). Each member carries ONE mate pad that docks it onto its PARENT part's
>   surface (pads do NOT pair with each other; keep-out is a separate concept). Coaxiality is a block
>   input, and it plus the pad docks DERIVE the parts' relative poses along a mate chain from a ROOT.
>   **D6b:** where/orientation of a mate is a PLAN duty; geometry only realizes the flush-seating
>   transform. The model-level `kinematics` entry is derived from the `joint`. Remaining open for
>   Slice B: the `joint`/mate plan entity shape and the root-anchor plan validation.
> - **Assembly structure -- DECIDED: recursive kinematic tree (D7).** Each node is authored in its
>   own frame; `placement` and `joint` unify into one parent EDGE (fixed = rigid placement, movable =
>   joint with a DOF). A movable edge re-poses the whole subtree, so series articulated chains
>   (hinged lid carrying a snap-lock) fall out by recursion. Flat plans = depth-1 trees (migration is
>   free; nothing breaks). Tree-only -- closed kinematic loops stay parked. Shape: **nested children**
>   (Option 1); a node does NOT know its parent -- it PUBLISHES a `union` interface the parent READS
>   (the `union` type is both the fuse pad and the upward attachment contract). Root = the node whose
>   edge parent is `world` = the world-anchored, fixed body (a PLAN judgment, usually the base part).
>   See "DECISION (D7)".
> - **dof datum -- DECIDED: authored pose.** Limits are read from the pose the block is drawn in;
>   revolute needs NO angular reference vector (see "dof vector model" below).
> - **Crux 1 (satisfaction algebra) -- single-axis (revolute + prismatic) SHIPPED via
>   `single-axis-joint-contract`; spherical (ball joint) is the one open fork.**

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

## Topology decision (D3): one block is the single source of a MATCHED PAIR

DECIDED: **Topology 1**, but on the correct rationale. The reason a joint's two members belong to
one block is **not** "they print in place together" -- it is that they are a **matched pair**: side A
and side B mate *only* with each other, and only when they share the same parameters. One block =
one parameter set = a guaranteed fit. Two independent half-blocks (today's lone `hinge_leaf`) let the
planner drift the two halves apart until they no longer mate. That is the anti-pattern this retires.

Manufacturing is irrelevant to the design: the two members may be printed together (print-in-place),
on separate plates, or on different printers entirely. The block emits the matched pair; the author
composes each member into whatever parent part it belongs to.

```
 TODAY (halves, one Workplane, unions=None)   MATCHED-PAIR BLOCK (multi-union)
 ──────────────────────────────────────────   ───────────────────────────────────────────
 dovetail_groove + dovetail_tongue          → one block → {groove, tongue}   prismatic
 ball_socket     + ball_stud                → one block → {socket, stud}      spherical (parked)
 hinge_leaf (lone half) / pin_hinge         → one block → {leaf_a, leaf_b}    revolute
 living_hinge (single flexure web, no pair)   unchanged: single body, no dof
```

The lone-half `hinge_leaf` is **retired**; a hinge block emits both leaves. `groove`/`tongue` and
`socket`/`stud` likewise fuse into single matched-pair blocks. Earlier framing that only
`pin_hinge` (the print-in-place case) qualified was wrong: the matched-pair guarantee applies to
every mating pair regardless of how it is printed.

### Composition: each member is a `union` fused into a parent part

A matched-pair block emits two member-unions; the author fuses each into its parent via the shipped
`union` interface (fuse-into-body). The two members can land in the **same** part (a standalone
print-in-place hinge) or in **different** parts (a door leaf and a wall leaf, printed separately):

```
 hinge block  →  { leaf_a, leaf_b }        (one parametric source, matched)
                    │        │
        union-into  │        │  union-into
                    ▼        ▼
              part: door   part: wall       (may be separate scripts / printers)
```

So the members are not "sub-bodies of one part" in general -- they are a matched pair distributed
across parts. This is why the per-part `resolve_unions` mechanism (crux 2) is necessary but not
sufficient: it names unions *within* one part; a joint's members may cross parts.

### DECISION (D6): a plan-level `joint` binding enforces the pair's single source (Option B)

Two ways the members reach two parts were on the table:

- **Option A -- call per part, same params.** `door.py` calls `hinge(P)["leaf_a"]`, `wall.py` calls
  `hinge(P)["leaf_b"]`; the match is only as good as the author using identical `P` on both sides.
  Nothing machine-checks it.
- **Option B (CHOSEN) -- a plan-level `joint` entity.** The plan declares a `joint` that names the
  block, its two member-unions, and which part each member fuses into. The pair's parameters come
  from ONE declared source (the joint's block + params), and validation can enforce that both member
  unions trace back to that single source -- so a mismatched pair is caught, not trusted.

Option B makes "these two really are a matched pair from one parametric source" *machine-verifiable*,
at the cost of a new plan entity and the wiring that fans one block's members out to their parent
parts. It also gives the joint contract (crux 1) a concrete home: the `joint` binding is where the
`dof` relates its two named members and where the satisfaction check reads the pair.

## D6 refinements (explore session): the mate model

Later exploration resolved most of D6's open sub-questions. Recorded here.

### Single source of params -- `parameters.py`

The matched pair's parameters live in a generated `parameters.py` imported by every script that
uses the block. One definition; the customer edits it, the LLM reads it back. Drift is impossible by
construction, so the "cross-script fan-out" worry dissolves -- and the part-per-`.py` file boundary
becomes cosmetic (everything could be one file). This is the concrete mechanism behind Option B's
"single parametric source."

### The pipeline is assembly-pose-first; fusion is in the ASSEMBLED frame

An earlier draft imagined fusing each member in its part's *local* frame and reconciling later. That
was wrong. The real flow:

```
 1. AUTHOR in assembly pose. A joint block emits {leaf_a, leaf_b} already coaxial in the
    ASSEMBLED frame (one block ⇒ coaxial by construction -- guarantee A).
 2. TRANSPOSE + FUSE, in assembled coords. Each union is placed into assembly coordinates
    (its mate pad gives the transform), then leaf_a ∪ door, leaf_b ∪ wall -- all in the SHARED
    frame. No part-local fusion.
 3. EXPORT assembly pose → the whole-model KINEMATIC CHECK (guarantee B).
 4. print_orientation / placement tears the unions apart and optimizes each one's bed pose
    (already a downstream, per-union step today).
```

### Mate pads dock a member onto its PART -- they do not pair with each other

Every union a block emits carries **one mate pad**: a surface/footprint that must touch a *suitable
surface of the part's union* it fuses into. Pads are one-sided glue interfaces (member → parent
body); `leaf_a`'s pad does **not** touch `leaf_b`'s pad. Coaxiality of the two members is NOT a pad
concern -- it is authored by the block (guarantee A) and is an *input*, not something to check.
(**Keep-out** areas are a separate, still-unspecified concept -- do not conflate them with mate pads.)

### Coaxiality is the input that DERIVES part poses (constraint chain, not a solver)

Because the block fixes `leaf_a ═ leaf_b` rigidly, and each pad docks its member onto a part, the
two parts' relative pose is *derived through the joint*:

```
   door ◀─pad─ leaf_a ══rigid (block)══ leaf_b ─pad─▶ wall
   ⇒ door-relative-to-wall is composed along the chain from a ROOT/datum part.
```

Assembly poses are **transform composition** along plan-declared mates from one anchored root -- not
an optimizer. `placement` shrinks to anchoring the root; every other union's pose derives.

### DECISION (D6b): where/orientation of a mate is a PLAN duty; geometry only realizes it

"Derive" is narrow. The **plan** decides which surface a pad mates to, *where* on it, and at what
orientation -- and how many joints (two hinges on the edges, one centered, three...). That is a
design decision, not a geometric constraint to solve. The **geometry** then derives only the exact
flush-seating transform (the offset along the surface normal so the pad sits on the face). Nothing is
searched or solved; the plan's mate intent is *realized*. This retires the earlier "keyed pad vs
graph-solvable / residual-DOF" worry -- the plan pins those DOFs by intent.

### Two guarantees, and the kinematics entry is DERIVED

- **Guarantee A (block):** the joint's own motion works in isolation (its two leaves swing 0-180
  without self-binding). Verified by the block author once; asserted by `dof.mechanical_limit`. No
  per-model check.
- **Guarantee B (model):** the joint's required range clears everything else in *this* assembly.
  This is the shipped whole-model kinematic check (moving union vs all other unions).

Because the `joint` knows its block (⇒ dof/axis), its members, and which parts they fuse into, the
model-level `kinematics` entry is **derived, not hand-written**: `moving_union` = the part a member
fused into; the assembled axis = block `dof` ∘ that part's derived placement; `required_range` from
the joint. The hand-written `kinematics` entry the single-axis contract shipped becomes the explicit
fallback; the derived form is the norm once joints exist.

### Remaining open for Slice B (the buildable core)

- **The `joint` / mate plan entity shape (sub-Q1).** How the plan expresses: block + params (via
  `parameters.py`), and per member `{member, part, surface, where, orientation}`. This is now the
  main design object.
- **Root/anchor + plan validation.** One part anchors the assembly frame; the rest derive along the
  mate chain. Validation must catch a part left *unanchored* (dangling from the chain) or
  *double-anchored* (conflicting mates) -- the plan-level analog of under/over-constraint.
- **Keep-out geometry** -- still unspecified; a distinct concept from mate pads (Slice C territory).

## DECISION (D7): the assembly is a recursive kinematic tree

The flat model (every part placed directly into the assembled frame; a flat `kinematics[]`) is a
special case. The real structure is a **kinematic tree** (scene graph / URDF-like):

```
   world
     └─ box            root: its edge to world is the ONE anchor placement
         └─ lid        edge = JOINT: revolute about the hinge, range 0–110°
             └─ lock   edge = rigid placement (snap-fit) in the LID's frame
```

- **Each node is authored in its own local frame.** A sub-agent designs the `lid` (and its `lock`
  child) without knowing anything about the `box`. Nodes are self-contained and reusable.
- **`placement` and `joint` unify into one parent edge.** Every node has exactly one edge to its
  parent: a **fixed** edge (rigid placement) or a **movable** edge (a joint with a DOF + range). A
  fixed edge is just a joint with zero range. The root's "placement into world" is its edge to the
  `world` node.
- **A movable edge re-poses the whole subtree.** Sweeping the hinge 0→110° rotates the `lid` frame,
  so `lock` (a child of `lid`) rides along automatically. This is how series articulated chains work
  (TODO "a moving union carries other unions") -- by recursion, not special-casing. The
  hinged-lid-with-snap-lock example falls out for free.
- **The sweep re-scopes to subtrees.** Today: `moving_union` vs "every other union". Tree: vary a
  joint edge → recompute its **subtree's** world poses → collide the moving subtree against the rest.
  The shipped kinematic check is the depth-1 leaf case; the dof/contract math is unchanged -- only the
  frame composition feeding it becomes recursive.

**Tree-only (scope boundary).** A tree has one path root→node, so this covers series chains but NOT
closed kinematic loops (a 4-bar linkage; a part hinged to two others). Closed loops need constraint
solving and stay in the parked multi-DOF/coupled territory.

**Migration (decided): flat plans are depth-1 trees.** Every existing part becomes a child of `world`
carrying its current `placement` as its (fixed) edge. The shipped pipeline is exactly the depth-1
instance, so nothing breaks; nesting is the generalization.

### The plan-tree shape (decided)

- **Nested children (Option 1).** The plan tree is expressed by nesting: each node carries its
  children and the edge to each. This mirrors the recursive structure literally. (The alternative --
  a flat `parts[]` + an edge list keyed by parent -- was considered and set aside; nesting matches the
  "author a node, declare its children" mental model.) Existing flat plans map on as depth-1 trees
  (every part a child of `world` with its current `placement` as a fixed edge).
- **A node does NOT know its parent; it PUBLISHES a `union` interface the parent READS.** A sub-part
  is authored in its own frame and *publishes* its `union` interface -- "here is my fuse pad and its
  pose in my frame" -- without knowing or naming who will read it. The **parent** reads that interface
  to transpose and fuse the child. So the child stays self-contained (publishes a contract, references
  no consumer), and the shipped `union` interface type does double duty: the member's fuse-into-parent
  pad AND the node's upward attachment contract. One concept, both roles -- no new primitive. The
  parent→child edge (fixed placement or a matched-pair joint) is owned by the parent side and names
  the block+params, the DOF, and which member fuses into parent vs child.
- **Root = the world anchor = the fixed body.** The root is the node whose edge parent is `world`; it
  is anchored to the world frame and is the body held fixed in the kinematic sweep, with every
  descendant moving relative to it. Choosing the root is a PLAN judgment (usually the base / ground
  part -- the thing bolted to the world), not a geometric one; re-rooting a tree is always
  geometrically valid because relative motion is symmetric, but the sensible rooting is the one that
  matches what is actually fixed in reality.
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
   DECLARED INTENT (block or author)               printed?  swept?  checked?
   1. JOINT CONTRACT    what MOVES (A↔B, moves[])    —        ✓        ✓
   2. MATING AREA       WHERE to connect (2D)         ✓        —        ✓   keep-out
   3. ASSEMBLY ENVELOPE keep-CLEAR-to-assemble (3D)   ✗        ✗        ✓   pseudo
   4. KEEP-OUT ZONE     author no-go volume (any 3D)  ✗        ✗        ✓   pseudo
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

### Declared keep-out zones (open-ended, not block-owned)

Mating-area and assembly-envelope keep-out are both BLOCK-declared: their shape and placement are
fixed by whoever wrote the block. A fourth case belongs to no block at all -- the **LLM (or user)
may declare a keep-out zone at will**, during planning or part authoring, as a *note to self*: a
negative constraint for a reason a block can't express (a screwdriver's swing to reach a boss, a
wire run reserved for a later part, clearance around a heat-set insert, "leave this corner alone,
it'll foul the enclosure lid"). Shape is unconstrained -- a union of primitives, in practice usually
one primitive (a box or cylinder).

The world carries every declared zone in one reserved union, `keep_out` (pseudo, per the
classification above: not printed, not swept, but checked). Any number of zones fuse into it; it
belongs to the world, not to any one part.

Gate check, run during the design loop like the other pseudo checks: every OTHER union's geometry
is intersected against `keep_out`. Any overlap rejects the design -- the OFFENDING geometry (not the
zone) is what gets redesigned. `keep_out` is itself exempt from export, from the kinematic sweep,
and from being checked against itself.

Mating-area and assembly-envelope keep-out (rows 2-3 above) are the two BLOCK-authored special
cases of this same underlying mechanism; `keep_out` (row 4) is the general, freeform, author-declared
case -- open-ended by design, since the author can't enumerate every reason to reserve a volume up
front.

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
- **Keep-out-zone check:** no union's geometry intrudes on the world's declared `keep_out` union.

## Cruxes

1. **Satisfaction algebra (crux 1) -- single-axis SHIPPED** via `single-axis-joint-contract`
   (type + placement-transformed axis; revolute coaxial, prismatic parallel; range vs
   `mechanical_limit`; spherical skipped). The remaining crux-1 items below are refinements /
   future work:
   - **A/B binding -- CORRECTED (see D6).** Earlier this was called "resolved -- the block owns both
     sides, so binding is trivial." That only holds when both members land in the SAME part. In
     general a joint's two members fuse into DIFFERENT parts (door leaf, wall leaf), so the binding
     lives in a plan-level `joint` entity (Option B / D6), not in the block. The shipped single-axis
     contract handles the one-block-one-dof case via the `kinematics` entry; the cross-part matched
     pair is the D6 work.
   - **Axis match -- SHIPPED.** Push the block-frame `dof` vectors through the union's
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
3. **Topology (D3, RESOLVED -> matched-pair block)** and **dof vector model (D4, RESOLVED ->
   authored-pose datum, no angular reference).** See the two decision sections above. The lone-half
   `hinge_leaf` is retired; hinge/dovetail/ball each become one matched-pair block.
4. **Composition + pair binding (D6, RESOLVED -> Option B).** A joint's two members are `union`s
   fused into parent parts (possibly different parts); a plan-level `joint` entity binds the pair to
   its single parametric source so a mismatched pair is machine-caught. Open sub-questions (joint
   entity shape, cross-script member fan-out, contract read path) are listed under D6 above; they are
   the core of the next change ("matched-pair joint blocks" / Topology-1 block merge).
