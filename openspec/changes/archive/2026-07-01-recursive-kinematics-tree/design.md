## Context

`kinematic_check.py` sweeps one `moving_union` per `kinematics` entry through its
`required_range` and tests it against a `CollisionManager` loaded with every other
union's assembled STL (see `src/kinematic_check.py:225-270`). That is correct for a
single joint bolted directly to a static body, but wrong for a chain: if `forearm` is
mounted on `shoulder` via its own joint, sweeping `shoulder` should carry `forearm`
(and anything mounted on `forearm`) along for the ride. Today it doesn't -- `forearm`
sits in the fixed set and the sweep reports a spurious collision the moment the
shoulder rotates into the space the forearm already occupies at rest.

`BUILD_PLAN.json`'s `kinematics` array (schema: `src/build_plan_schema.json`) has no
field today that expresses "this joint is mounted on that joint," so the chain can't
even be declared.

**Relationship to the decided Slice B tree (D7).**
`openspec/changes/archive/2026-07-01-joint-contract/design.md` ("D7: Assembly
structure is a recursive kinematic tree") already decided the fuller shape of this
problem: `placement` and `joint` unify into one parent edge per node, the whole
plan (parts, not just `kinematics` entries) nests into a tree, and matched-pair
joint blocks + a plan-level `joint` entity replace independently-authored halves.
That is filed as "Slice B -- NEXT" and is explicitly not yet buildable (open
schema questions for the nested node + its edge). This change deliberately does
NOT implement Slice B. It takes only the resolved shape decisions that transfer
directly -- nested `children` (not a parent back-reference), parent-owns-the-edge,
tree-only (no closed loops) -- and applies them to the narrower, already-buildable
problem of the `kinematics` array's sweep on today's flat `parts`/`placement`
schema. `moving_union` stays a plain id-reference into the existing flat
`parts[].unions`; no block merging, `union`-interface docking, or pose derivation
is introduced here. The two are compatible: Slice B, when it lands, can derive
`kinematics` entries from its edges instead of them being directly authored,
without invalidating the subtree-sweep logic this change adds.

A related design principle established elsewhere in this project: a node should
know its own children (what attaches to it) but not its ancestors (what it hangs
off of) -- e.g. a lid knows the lock mounted on its edge, but not that it hangs off
a box. Applied here, the joint closer to the static frame (`shoulder`) should
declare what's mounted on it (`forearm`), not the other way around. That also
happens to be the better data shape for this problem independent of the principle:
nesting children directly inside their mount point makes the `kinematics` array a
literal tree instead of a flat list simulating one via back-references.

## Goals / Non-Goals

**Goals:**
- Let a `kinematics` entry declare its `children` -- the joints mounted on it --
  nesting the `kinematics` array into a forest instead of a flat list with
  back-references.
- When sweeping a joint, carry its entire descendant subtree (everything nested
  under its `children`, at any depth) along with the same per-step transform, and
  only treat unions outside that subtree as fixed obstacles.
- Apply the existing per-entry checks (`moving_union` resolves, block/dof exists,
  joint contract) uniformly regardless of nesting depth in `plan_validate.py`.

**Non-Goals:**
- Composing simultaneous multi-joint motion (e.g. sweeping shoulder and elbow
  together to find combined-motion collisions). Each entry is still swept in
  isolation with every other joint (ancestor, descendant, or unrelated) held at its
  own authored zero pose -- exactly what the assembled STL already represents.
- Rigid grouping of a plain (non-jointed) union to a moving union. `children`
  only nests `kinematics` entries inside each other; a decorative union bolted to a
  moving forearm with no joint of its own has no way to ride along, same as today.
- Changing the joint-contract axis/range checks (`joint-contract` spec) -- those are
  per-entry and unaffected by tree topology.

## Decisions

### `children` nests entries recursively; no back-reference, no separate structure

Alternatives considered:
- A `parent_union` back-reference field on the child entry. Rejected: it puts the
  reference on the wrong node (the distal joint has to know about something above
  it), requires explicit cycle detection since nothing in a flat list-plus-pointer
  structure prevents a reference loop, and needs a reverse-lookup pass
  (`moving_union -> entry`) before any subtree can be computed.
- A separate top-level `kinematic_tree` mapping alongside the flat `kinematics`
  array. Rejected -- splitting the tree from the entries it describes invites the
  two structures drifting out of sync.

`children` is an array of full nested `kinematics` entries (same shape,
recursively) mounted on this entry's `moving_union`. A top-level entry (not nested
under anyone's `children`) is mounted on the static frame -- identical to today's
implicit behavior, so every existing plan without `children` is unaffected. Because
a child is placed physically inside its parent's JSON object, a joint cannot be its
own ancestor: the structure is acyclic by construction, and `plan_validate.py`
needs no cycle-detection pass at all.

### Descendant subtree collected by a plain recursive walk of `children`

For entry `E`, the swept subtree is `E` plus every entry transitively reachable by
descending into `children` -- a direct recursive walk, no reverse-lookup map
needed. During `E`'s sweep, at each step the transform computed for `E`'s
`moving_union` (rotation/translation per `iter_poses`) is applied to `E`'s mesh and
to every descendant's mesh identically -- not recomputed relative to each
descendant's own frame. This is valid because the transform is a rigid motion
applied in the shared assembled frame, and every union's assembled STL already
encodes its authored (zero-angle) pose in that frame; rigidly carrying it through
`E`'s transform is exactly "held at zero relative angle while riding `E`." The
alternative -- composing each descendant's own dof into the sweep -- is the
explicitly excluded multi-joint composition goal.

### Fixed set becomes "all unions minus the swept subtree"

`kinematic_check.py` currently derives the fixed set as `all_union_ids - {moving_id}`
(`src/kinematic_check.py:233`). It becomes `all_union_ids - subtree_ids`, where
`subtree_ids = {moving_id} | descendants(moving_id)` from the recursive walk above.
The `CollisionManager` still adds each fixed union as a separately named object
(unchanged); only its membership changes. The moving side changes from a single
mesh to a list of `(union_id, mesh)` pairs, each transformed identically per step
and each checked against the manager; the first hit at a step (from any subtree
member) reports that step's value and the colliding fixed union(s), same issue
shape as today.

### Validation recurses into `children` instead of walking a parent chain

`plan_validate.py`'s `_check_kinematics` flattens the forest with a simple
recursive traversal (visit an entry, recurse into its `children`) and runs the
existing per-entry checks (`moving_union` resolves to a union id, block/dof exist,
joint contract type/axis arms) on every entry regardless of depth. There is no
`parent_union` to resolve and nothing to detect as a cycle.

## Risks / Trade-offs

- **Residual gap: non-jointed rigid attachments still don't ride along.** A plain
  union welded to a moving forearm (no joint of its own) stays in the fixed set and
  will produce the same false-positive collisions this change fixes for joint
  chains. This is unchanged from today's behavior (not a regression) and is called
  out as future work (a rigid-grouping declaration independent of `kinematics`),
  not silently claimed as fixed.
- **Ambiguous multi-entry mounting.** Two entries can already declare the same
  `moving_union` today; this change doesn't add new validation for that case. If it
  happens (e.g. as siblings under the same `children` array, or in unrelated
  branches), both are treated as separate tree nodes with that union id, which may
  double-count the union in a subtree walk. Not addressed here since it predates
  this change and no plan in the repo does this.
- [Deep/wide trees inflate sweep cost per joint, since every subtree member is
  transformed and collision-checked at every step] -> mitigated by real assemblies
  having shallow chains (a handful of links at most); no batching optimization
  needed for v1.
- **Recursive JSON Schema.** `children` referencing the same entry shape requires a
  self-referencing `$ref` in `build_plan_schema.json` (draft-7 supports this via a
  named definition). Slightly less readable than the rest of the schema's flat
  definitions, but confined to one property.

## Open Questions

None -- scope is deliberately bounded to single-joint-at-a-time sweeps with rigid
subtree carry-along, matching the existing sweep's per-entry structure.
