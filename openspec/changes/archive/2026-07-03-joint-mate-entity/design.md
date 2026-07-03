## Context

`pin_hinge` already returns `{"leaf_a": ..., "leaf_b": ...}` from one call -- a matched pair, per
the archived `2026-07-01-joint-contract` design's D3 decision. But `BUILD_PLAN.json` has no entity
that says "leaf_a fuses into part `door`, leaf_b fuses into part `wall`." Today, `door` and `wall`
each need their own independently hand-authored `placement` (`src/placement.py`) to land in the
right place in the assembled frame -- there's no way to say "wall's pose follows from door's pose
plus the hinge," so an author must compute that arithmetic by hand, and nothing catches a part left
disconnected from the assembly or given two conflicting positions.

The archived design names this "the buildable core" of Slice B (D6/D6b, "Remaining open for Slice
B") and works out most of the mechanics in prose: a plan-level `joint` entity, one shared param
source (`parameters.py`, explicitly deferred here -- see proposal.md), members docking onto parts
(D6b: "the plan decides which surface a pad mates to, where on it, and at what orientation"), and
pose composed along a mate chain from an anchored root (D7). This design turns that prose into a
concrete, buildable schema and algorithm.

## Goals / Non-Goals

**Goals:**
- A `joint` plan entity naming a matched-pair block, its two members, and which part each fuses
  into.
- A `dock` transform per member (reusing the existing `placement` rotate/translate shape) describing
  where that member sits within its host part's own authored frame -- the concrete answer to D6b's
  "where/orientation is a plan duty."
- Derive a mated part's assembled-frame pose by composing the mate chain from one anchored
  `root_part`, instead of requiring every mated part to carry its own `placement`.
- Validate the mate graph: every joint-participating part reachable from `root_part` along exactly
  one path (no cycles, no double-anchoring, no orphans).

**Non-Goals:**
- **`parameters.py` generation.** This change does not make two member scripts' block calls
  machine-guaranteed to share literal params -- see proposal.md's explicit deferral.
- **Deriving `kinematics` from a `joint`.** Stays hand-written for now.
- **Mate-area / keep-out geometry** (Slice C) -- unrelated.
- **Merging dovetail/ball into matched-pair blocks.** `pin_hinge` is the only one that exists; this
  design works for any block that declares `emits`, whenever more are merged.
- **Multiple independent mate-trees in one plan.** Exactly one `root_part`; a plan needing two
  physically disconnected mated sub-assemblies isn't supported in v1 (an artificial limitation, not
  a physical one -- see Open Questions).
- **Auto face-normal seating.** `dock` is an author-supplied transform, not solved from a named
  surface -- the richer mate-area model (which surface, where on it) is future work.

## Decisions

### The mate-pose formula: `world_pose(part_B) = world_pose(part_A) . dock_A . inverse(dock_B)`

A matched-pair block returns both members already expressed in **one shared local frame** (call it
`F` -- the block's own authoring frame; this is exactly what "coaxial by construction" means in the
archived design). Part A's script docks member A into its own authored frame via `dock_A`
(`F -> DF_A`); part B's script docks member B into its own frame via `dock_B` (`F -> DF_B`). Frame
`F` is physically **one joint** with exactly one embedding into the assembled/world frame, so the
two paths into the world must agree as transforms, not just at a point:

```
world_pose(A) . dock_A  =  world_pose(B) . dock_B      (both map F -> world)
```

Solving for the unknown side gives the derivation formula. Given `world_pose(A)` (root, or already
derived) and both `dock` transforms declared in the `joint` entry, `world_pose(B)` is computed
exactly -- not solved for or optimized. `dock_A`/`dock_B` reuse `placement.py`'s existing
`to_matrix()` (already a 4x4 numpy transform builder for the same rotate-then-translate shape), and
the inverse of a rigid transform is always well-defined (`numpy.linalg.inv`), so no new transform
math is needed beyond one matrix multiply and one inverse per hop.

Alternative considered: treat the two `dock`s as independently authored and solve/optimize for a
best-fit relative pose. Rejected -- there is nothing to solve; the formula is exact once both docks
are declared, and "solving" would hide an author mistake (a genuinely wrong dock) behind an
approximate fit instead of surfacing it.

### `dock` reuses the `placement` shape, applied at a different point in the frame chain

Rather than invent a new mate-transform vocabulary, a member's `dock` is exactly a `placement`
object (ordered `rotate` + `translate_mm`), identity when absent. The only difference is what frame
it maps into: a part's own `placement` maps that part's authored geometry into the **assembled**
frame; a member's `dock` maps the block's shared frame into the **member's host part's own
authored** frame. Reusing the shape means `placement.py`'s `to_matrix`/`apply_cq` need no changes,
and the concept an author already knows (rotate steps + a translation) transfers directly.

### `emits` closes the mesh-free member-id check

Nothing today lets `plan_validate.py` catch a `joint` entry naming a member id the block doesn't
actually produce (e.g. a typo'd `"leaf_c"`) before any part script runs -- that failure would
currently only surface via `units.resolve_unions`'s runtime dict-key check, deep in the part loop.
Adding `emits` (the block's member ids, e.g. `["leaf_a", "leaf_b"]`) to a matched-pair block's
inventory descriptor -- alongside the existing `dof` -- lets `_check_joints` validate this
mesh-free, matching the pipeline's existing "catch it as early as possible" philosophy (the same
reasoning behind `dof`, `blocks_needed[].extents_mm`, and the thin-interface script-level check).

### The mate graph is a tree from one `root_part`; cycles and orphans are both errors

Mirrors the tree-only boundary `recursive-kinematics-tree` already established for the kinematics
array (D7: "tree-only... NOT closed kinematic loops"), applied here to the mate graph instead of the
motion graph:

- A part named in some joint's `members` but not reachable from `root_part` -> **unanchored**.
- A part reachable from `root_part` via more than one path (a cycle: e.g. three joints closing a
  loop A-B-C-A) -> **conflicting mate path**, rejected. This is the same closed-loop exclusion as
  D7, now applied to static mate chains instead of moving subtrees.
- A part reachable via the mate chain that ALSO declares its own `placement` -> **double-anchored**
  (ambiguous: which pose wins?). `root_part` is exempt -- its own `placement` (or absence, meaning
  identity) is exactly its edge into the world, unchanged from today's mechanism.
- Two members of one `joint` naming the **same** part is rejected: a same-part matched pair (e.g. a
  standalone print-in-place `pin_hinge` part) already has a mechanism -- the part's own `unions`
  array -- and needs no mate-chain derivation at all (there is only one part, hence only one
  authored frame; nothing to compose).

### `model_export.py` substitutes the derived pose only for mate-chain parts

A part not named in any `joint`'s `members` is entirely unaffected -- it keeps using its own
`placement` (identity when absent), exactly as `assembly-phase` already specifies. Only a part
reached via the mate chain has its pose **replaced**: the exporter computes it once (a pure
pose-composition pass over `joints`, no mesh involved) and uses that 4x4 transform wherever it
would otherwise have read the part's `placement`.

## Risks / Trade-offs

- **`dock` can still drift from what the script's CadQuery code actually built**, the same way a
  part's own `placement` can already drift from what its script authored today -- this is an
  existing, accepted class of risk (author discipline), not a new one this change introduces.
- **No `parameters.py` yet** means the two member scripts' block calls can still literally
  hand-diverge in their params even though the mate chain and member ids are now validated -- the
  entity gives the plan a place to declare one shared source, but doesn't yet wire scripts to read
  it. Flagged clearly in the proposal as deferred, not silently unsolved.
- [A part's derived pose silently becomes wrong if `dock` is declared backwards (A/B swapped)] ->
  mitigated by the formula being symmetric in structure (swapping which side is "known" just swaps
  which `dock` gets inverted), so plan_validate can't catch an author's semantic swap -- this is the
  same class of risk as an author swapping `axis_dir`/`axis_origin_mm` in a `kinematics` entry today
  (caught downstream by the whole-model kinematic sweep reporting an implausible collision, not by
  schema validation).

## Open Questions

- **Single vs. multiple `root_part`s.** V1 requires exactly one anchor; a plan with two physically
  disconnected mated sub-assemblies has no clean expression yet (give each its own `placement` and
  don't connect them via `joints` -- which works today without this feature at all). Worth
  revisiting if a real design needs two independently-anchored mate trees in one plan.
- **Whether `emits` should also record each member's own local origin/axis** (beyond the bare id),
  which could later let `plan_validate` sanity-check a `dock`'s plausibility against the block's own
  geometry bounds. Not needed for this change's validation; left for whoever tackles auto
  face-normal seating.
