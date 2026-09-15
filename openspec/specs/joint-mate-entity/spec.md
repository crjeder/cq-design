# Joint Mate Entity

## Purpose

Defines requirements for cross-part matched-pair joints: how a block declares the member
ids it emits, how the build plan wires those members to parts via a `joints` array, how
the resulting mate graph is validated as a single tree rooted at `root_part`, and how a
mated part's assembled pose is derived by composing the mate chain instead of an authored
`placement`.

## Requirements

### Requirement: A matched-pair block declares its member ids via `emits`

A block whose function returns a `dict[str, Workplane]` of matched members (e.g. `pin_hinge`) SHALL
declare an `emits` array on its `blocks/inventory.json` descriptor, alongside the existing `dof`:
the exact set of member ids the block's returned dict uses (e.g. `["leaf_a", "leaf_b"]`). A block
with no `emits` is not usable as a `joint` entry's `block`. `emits` SHALL contain exactly two ids
(the matched pair); a block emitting more than two sub-bodies, or exactly one, is out of scope for
this requirement.

#### Scenario: A matched-pair block declares its two member ids
- **WHEN** `pin_hinge`'s inventory descriptor is read
- **THEN** it carries `emits: ["leaf_a", "leaf_b"]`

#### Scenario: A block without emits cannot back a joint entry
- **WHEN** a `joint` entry names a `block` whose inventory descriptor has no `emits`
- **THEN** plan validation fails, reporting the block cannot back a `joint`

---

### Requirement: The build plan declares cross-part matched-pair joints via a `joints` array

`BUILD_PLAN.json` SHALL support an optional top-level `joints` array. Each entry SHALL declare
`joint_id`, `block` (a block name carrying `emits`), `params` (an object of kwargs passed to the
block's function call -- the single declared source for this pair's parameters), and `members`: an
array of exactly two objects, each `{member, part, dock}`. `member` SHALL be one of the block's
declared `emits` ids (the two members of one joint referencing the block's two distinct `emits`
ids, not the same one twice); `part` SHALL be an existing part id; `dock` is optional (identity when
absent) and reuses the existing `placement` shape (ordered `rotate` steps then `translate_mm`), but
describes the member's pose **within its host part's own authored frame**, not the assembled frame.
The plan SHALL also support an optional top-level `root_part` (a part id), required when `joints` is
non-empty: the one part anchored directly into the world (its own `placement`, unchanged from
today's mechanism, or identity when absent).

#### Scenario: A joint names its block, params, and two members
- **WHEN** a hinge joins a `door` part and a `wall` part
- **THEN** the plan's `joints` entry declares `block: "pin_hinge"`, `params` with the hinge's
  dimensions, and `members: [{member: "leaf_a", part: "door", dock: ...}, {member: "leaf_b", part:
  "wall", dock: ...}]`

#### Scenario: A joint member naming an unknown emits id is rejected
- **WHEN** a `joints` entry's member names `"leaf_c"` but the block's `emits` is
  `["leaf_a", "leaf_b"]`
- **THEN** plan validation fails, reporting the member id is not one the block emits

#### Scenario: A joint's two members naming the same emits id is rejected
- **WHEN** a `joints` entry declares both members with `member: "leaf_a"`
- **THEN** plan validation fails: a joint's two members must reference the block's two distinct ids

#### Scenario: A joint's two members naming the same part is rejected
- **WHEN** a `joints` entry's two members both name `part: "hinge_body"`
- **THEN** plan validation fails: a same-part matched pair uses the part's own `unions` array, not
  a `joints` entry

#### Scenario: Plan without joints skips the mate-chain stage
- **WHEN** a plan has no `joints` array or an empty one
- **THEN** no `root_part` is required, and every part keeps using its own `placement` unchanged

---

### Requirement: The mate graph is validated as a single tree rooted at `root_part`

`plan_validate.py` SHALL treat each `joints` entry as an edge between its two members' parts and
validate the resulting graph: every part named in some `joints` entry SHALL be reachable from
`root_part` along **exactly one** path. A part reachable via more than one distinct path (a cycle)
SHALL be rejected as a **conflicting mate path** -- closed kinematic loops are out of scope, the
same tree-only boundary already established for the `kinematics` array. A part named in some
`joints` entry that is NOT reachable from `root_part` SHALL be rejected as **unanchored**. A part
reachable from `root_part` via the mate chain that ALSO declares its own `placement` SHALL be
rejected as **double-anchored** (an ambiguous conflict between the derived and the authored pose);
`root_part` itself is exempt from this rule.

#### Scenario: A part disconnected from root_part is rejected
- **WHEN** a `joints` entry links two parts neither of which is `root_part` nor reachable from it
- **THEN** plan validation fails, reporting both parts as unanchored

#### Scenario: A cycle in the mate graph is rejected
- **WHEN** three `joints` entries connect parts A-B, B-C, and C-A, forming a loop
- **THEN** plan validation fails, reporting a conflicting mate path

#### Scenario: A mate-chain part with its own placement is rejected
- **WHEN** a part reachable from `root_part` via one `joints` entry also declares its own
  `placement`
- **THEN** plan validation fails: the part is double-anchored

#### Scenario: root_part's own placement is not double-anchoring
- **WHEN** `root_part` declares a `placement` and is also named in a `joints` entry's members
- **THEN** plan validation passes: `root_part`'s `placement` is its edge into the world, not a
  conflict

---

### Requirement: A mated part's assembled pose is derived by composing the mate chain

A mated part's assembled pose SHALL be derived by composing its `joints` mate chain. For an entry
linking member A (on a part whose world pose is already known -- `root_part` or already derived) and
member B (on the part to derive), the world pose of part B is computed as
`world_pose(part_B) = world_pose(part_A) . dock_A . inverse(dock_B)`, where `dock_A`/`dock_B` are
each member's declared `dock` transform (identity when absent). This holds because a matched-pair
block returns both members already expressed in one shared local frame with exactly one physical
embedding into the assembled frame, so the two paths into that frame via each part must agree; the
formula is exact, not solved or optimized for. The model-level export SHALL use this derived
transform in place of a part's own `placement` for every part reached via the mate chain, walking
outward from `root_part`.

#### Scenario: A mated part's pose follows from its neighbor's pose and both docks
- **WHEN** `root_part` is `door` (identity placement) and a `joints` entry links `door`'s `leaf_a`
  (dock: identity) to `wall`'s `leaf_b` (dock: rotated 180 degrees about Z)
- **THEN** `wall`'s derived world pose is `door`'s world pose composed with the identity dock and
  the inverse of the 180-degree-Z dock

#### Scenario: A derived pose replaces the part's own placement in export
- **WHEN** a part is reached via the mate chain from `root_part`
- **THEN** the model-level export positions that part's union using the derived transform, not any
  `placement` field on the part (which the tree-validation requirement above forbids it from having)

#### Scenario: A part outside every mate chain is unaffected
- **WHEN** a part is not named in any `joints` entry
- **THEN** its assembled pose still comes solely from its own `placement` (identity when absent),
  exactly as before this capability existed

### Requirement: An interface name shared by two unlinked parts is reported

`plan_validate.py` SHALL report a plan-validation finding when one
`interfaces[].name` is declared on two or more parts that no `joints` entry links.
Two parts are linked when a single `joints` entry names both of them across its two
`members[].part` values. The finding SHALL name the interface and the parts holding
it, and SHALL point at `joints` / `mate_chain.py` as the derivation route.

The finding is advisory: it SHALL NOT be returned by `validate_plan` and SHALL NOT
make the plan invalid, so it never reaches the quality gate's `plan_invalid` path. It
SHALL be printed by `plan_validate.main()` after the plan passes, alongside the
existing thin-block and deferred-axis-arm findings. Interfaces with no `name` SHALL
be skipped.

#### Scenario: A shared pivot bore is declared twice with no joint
- **WHEN** a plan declares an interface named `pivot_bore` on both `cradle` and
  `plate`, and `joints` contains no entry naming both parts
- **THEN** `plan_validate.main()` prints a finding naming `pivot_bore`, `cradle` and
  `plate`
- **AND** `validate_plan` still returns an empty error list

#### Scenario: The shared feature is routed through a joint
- **WHEN** the same plan adds a `joints` entry whose two members are `cradle` and
  `plate`
- **THEN** no finding is reported for `pivot_bore`

#### Scenario: A name used by one part only
- **WHEN** an interface name appears on exactly one part, or an interface declares no
  `name`
- **THEN** no finding is reported for it

#### Scenario: Three parts share a name, one pair is linked
- **WHEN** `pivot_bore` is declared on `cradle`, `plate` and `strut`, and one
  `joints` entry links `cradle` and `plate`
- **THEN** one finding is reported naming `strut` as the unlinked holder of
  `pivot_bore`
