## Context

`blocks/joints.py` holds one mechanism (sliding dovetail) as two functions that are
identical except for a `clearance` term. The library needs more joints, but the
driver that makes joints matter for FDM is anisotropy: the layer bond is the weak
axis, so a load along Z cannot be fixed by thickening - the part must be split and
each half printed flat, then rejoined. The joint that rejoins them must not
reintroduce a Z-weak path: it has to carry the seam load in shear / mechanical
interlock, and (since most strength-splits are also glued) ideally add bond area and
registration too.

The agent that selects a block reads `blocks/inventory.json` by `name` and
`interfaces`. So the classification that matters is the one the agent reasons with -
a *functional* one - not the geometry's internal construction.

## Goals / Non-Goals

**Goals:**
- A functional taxonomy a selector can act on: what motion the joint allows after
  assembly, and whether it comes apart again.
- Five new mechanisms covering the strength-split (finger, mortise/tenon, dowel),
  articulation (ball), and folding (hinge) use cases.
- One shared notion of fit (`clearance`) that spans every pair and sets the
  separable/permanent behaviour, instead of a per-joint constant.
- Deduplicate: dovetail and finger joints share an extrude-profile core.

**Non-Goals:**
- No split helper (cut-plane + auto-stamp mating joints). Out of scope; blocks are
  placed manually.
- No living hinge (anisotropy delamination; material-dependent).
- No tiled-dovetail / half-lap / annular snap in this pass.
- No change to the runner, part loop, or BUILD_PLAN schema.

## Decisions

**Two orthogonal taxonomies, two layers.** The properties the user listed -
"hinge moves on one axis", "dovetail can be reopened", "press-fit is permanent" -
are really two independent axes: *motion* (rigid / hinge / ball) and *reversibility*
(separable / permanent). Crossed, they form a selection matrix:

```
                SEPARABLE                   PERMANENT
  RIGID      sliding dovetail, snap clip   finger+glue, mortise/tenon+glue,
                                           press-fit dowel
  HINGE      loose-pin hinge               pinned / print-in-place hinge
  BALL       ball snap-in socket           captured / in-place ball
```

This functional taxonomy drives `inventory.json` metadata (`motion`, `reversible`).
The construction taxonomy (extrude / revolve / tiled-cylinder) drives only the
private code organization and is never exposed. Keeping them separate is the whole
point: the agent selects by intent, the implementation is free to share cores.

**Reversibility is set by fit, not only geometry.** A finger joint at +0.1 mm
clearance is a separable test fit; the same joint glued is permanent. A dowel at a
+0.1 mm gap is separable; at -0.1 mm interference it is a permanent press-fit. So
`clearance` is a first-class parameter on every pair (positive = gap, negative =
interference), and `reversible` in the inventory records the joint's *default* fit,
not an immutable property. This is why "press-fit" is not a separate block - it is a
clearance regime applied to the dowel/tenon/finger geometry.

**`carries` load-direction metadata.** Because the strength-split use case needs the
seam to carry load in the right direction, each joint declares which directions it
transmits across the seam (e.g. `["shear-xy", "lock-z"]` for a dovetail). This lets
a selector match a joint to the load at a chosen split plane. Optional field; absence
means unspecified.

**Three construction cores, sharing only fit + role.** The mechanisms do not reduce
to one core:
- *extrude-profile* (2D section -> extrude -> optional tile): dovetail, finger,
  tenon/mortise.
- *revolve* (spherical / cylindrical of revolution): ball stud + socket, dowel.
- *tiled-cylinder* (alternating knuckles on an axis + pin): hinge.
They share exactly two conventions: a `clearance` fit modifier and a positive/negative
role (add vs subtract). Those two are the only thing worth centralizing; forcing a
single core would be the over-abstraction the repo's conventions warn against.

**Mate pairs follow existing naming.** Each joint is a pair mirroring
`alignment_pin`/`alignment_socket` and `dovetail_groove`/`dovetail_tongue`: a
positive member to union and a negative member to subtract (or, for hinge/finger, a
`side`/`start_high` flag selecting the complementary half). The negative member is
the positive profile grown by `clearance`.

**Ball socket is slotted snap-in by default.** A slot lets the cup flex over a ball
captured past its equator without a Z-crossing living-hinge flex. Print-in-place ball
is deferred; the snap-in slotted socket prints flat and assembles by hand.

**Hinge ships two variants, not four.** `pin` (separate rod/filament/metal through
bored knuckles) and `print-in-place` (knuckles printed with a clearance gap, no
assembly) cover the overwhelming majority of uses. Snap-fit hinge reuses the ball
idea later; living hinge is excluded.

## Schema impact

`blocks/inventory_schema.json` uses `additionalProperties: false` at the item level
and a closed interface-`type` enum. Both must change:
- add optional `motion` (enum: rigid|hinge|ball), `reversible` (boolean), `carries`
  (array of strings) to item properties;
- extend the interface `type` enum with `hinge_axis`, `ball`, `ball_socket`,
  `finger`, `mortise`, `tenon`, `dowel`.
Existing entries remain valid (new fields optional). `blocks/validate.py` continues
to validate against the updated schema.

## Risks / Trade-offs

- [Three cores instead of one] -> accepted; they share fit+role and nothing else.
  Collapsing them would couple unrelated geometry. Matches the "three similar lines
  over a premature abstraction" rule.
- [Negative clearance press-fit is print-tuning-dependent] -> document a PLA default
  (~-0.1 mm radial) and note FDM hole-shrink compensation; do not auto-compensate.
- [Print-in-place hinge clearance is orientation-critical] -> the inventory `use:`
  string states the required print axis, as the dovetail entry already does.
- [Schema change touches a shared file] -> additions are optional/backward-compatible;
  a validation task confirms existing entries still pass.
- [Metadata the part loop does not yet read] -> `motion`/`reversible`/`carries` are
  advisory now; they cost nothing and unblock a future selector without a second
  schema migration.

## Open questions (to resolve during apply)

- Should `carries` use a fixed vocabulary (`shear-xy`, `lock-z`, `tension`, ...) or
  free strings? Leaning fixed, but defer until the first selector consumes it.
- Exact default `clearance` per mechanism (sliding vs snap vs press) - tune against
  printed test coupons in the verify step.
