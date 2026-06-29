# Design: add-union-interface-type

## Decision 1: `union` is a vocabulary addition, not a new descriptor shape

`union` is added to the same closed `type` enum every other interface uses; an interface
descriptor keeps its existing required shape (`type`, `orientation`, `origin`). No new
fields. This keeps the change additive and backward compatible: every existing inventory
entry stays valid, and a `union` interface is authored exactly like any other
(`{"type": "union", "orientation": "+Z", "origin": [x, y, z]}`), where `orientation`/`origin`
locate the fused face/region in block-local coordinates.

## Decision 2: Semantics -- fused body, not a mate or a joint

The vocabulary already encodes two relationships and `union` adds the third:

- **mating docks** (`face_mount`, `snap_hook`/`snap_socket`, `dovetail`/`finger`/`mortise`/
  `tenon`, `pin`/`socket`, ...): the interface joins this block to a **separately printed**
  part across an assembly seam.
- **kinematic axes** (`axis`, `hinge_axis`, `ball`/`ball_socket`, ...): the interface defines
  a **moving** joint.
- **`union`** (new): the interface marks where the block is **rigidly fused** (boolean
  `union`) into its parent part's body -- one printed rigid body, no seam, no motion.

This is the distinction the membership-derivation work needs: two blocks joined by a `union`
interface belong to the same part/union; a `face_mount` crosses a part boundary. The change
only *defines and documents* this; it does not yet build the derivation.

## Decision 3: Keep the two sources of truth in lock-step

The vocabulary is enforced in two places that must agree: the JSON Schema enum
(`inventory_schema.json` `interfaces.items.properties.type.enum`) and the Python
`_VALID_INTERFACE_TYPES` frozenset in `blocks/validate.py`. Both get `union`. (They are
already drifting -- the schema enum carries `finger`/`mortise`/`tenon`/`dowel`/`ball` that
the spec's listed set omits -- so this change also realigns the **spec** text to the
implementation, but does not attempt to dedupe the two runtime sources; that refactor is out
of scope.)

## Decision 4: Spec list reflects reality

The `block-library` "closed set" requirement is rewritten to enumerate the full vocabulary
actually enforced today plus `union`, rather than the stale subset. This makes the modified
requirement truthful instead of encoding a list that the schema already contradicts. A new
requirement captures the `union` semantics (fused-to-body, same rigid body) so the meaning,
not just the token, is specified.

## Decision 5: Guidance lives in planning.md

The planner chooses interface types when emitting blocks into `BUILD_PLAN.json`, so the
"union vs dock vs axis" note goes in `prompts/planning.md` next to the existing interface
guidance. The schema `type` description gets a one-line gloss for authors reading the schema
directly. No change to `part.md` (it consumes interfaces, it does not classify them).
