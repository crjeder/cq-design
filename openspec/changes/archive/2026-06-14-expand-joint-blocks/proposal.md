## Why

`blocks/joints.py` has exactly one joint mechanism: the sliding dovetail. But the
single most overlooked reason to split a 3D model is **anisotropy**: FDM parts are
weakest across the layer bond (~50-70% of in-plane strength), so a feature loaded
along Z is structurally doomed no matter how thick it is. The fix is to split the
model and print each half flat, with its critical load in-layer, then rejoin. That
requires a vocabulary of joints the assembly layer can compose, classified by what
the *user* needs (does it still move? can it come apart again?), not by how the
geometry happens to be built.

The existing `dovetail_groove`/`dovetail_tongue` pair is also near-duplicated code
(identical except a `clearance` term), which is the signal that the next joints
should share a small construction core rather than each be hand-authored.

## What Changes

- **Two-axis functional taxonomy** for joints, recorded as new optional inventory
  metadata: `motion` (rigid | hinge | ball) and `reversible` (true | false), plus a
  `carries` load-direction list. This is the layer by which a joint is *selected*.
- **Schema change**: `blocks/inventory_schema.json` gains the three optional fields
  and new interface `type` enum values (`hinge_axis`, `ball`, `ball_socket`,
  `finger`, `mortise`, `tenon`, `dowel`). `additionalProperties: false` currently
  forbids the new fields, so the schema must be extended.
- **Five new joint mechanisms** in `blocks/joints.py`, each a matched pair, built on
  three private construction cores (extrude-profile, revolve, tiled-cylinder):
  - `finger_joint` (box joint) - interlocked shear + glue area
  - `tenon` / `mortise` (rectangular) - keyed peg + pocket
  - `ball_stud` / `ball_socket` (snap-in, slotted socket) - articulation
  - `hinge_leaf` (pin and print-in-place variants) - one-axis folding
  - `dowel_pin` / `dowel_bore` - load-bearing alignment, fit-selectable
- **`clearance` becomes the first-class fit modifier** across all pairs: a positive
  gap yields a separable fit, a negative value yields an interference (press) fit.
  The same geometry moves between "separable" and "permanent" by this parameter.
- No changes to existing blocks, the runner, or the part loop. `dovetail_groove`/
  `dovetail_tongue` are refactored onto the shared extrude core without API change.

## Non-Goals

- **No split helper.** Cutting a solid on a plane and stamping the mating joint onto
  both faces is a separate, larger feature. These blocks are placed manually by the
  assembly layer, exactly like every other block today.
- **No living hinge.** A thin flexure printed flat bends across layer lines and
  delaminates in PLA; it is material-dependent and deferred.
- **Deferred to a second pass:** tiled (corner) dovetail, half-lap, annular snap.
  The cantilever snap-fit already exists as `snap_hook_clip` and is reused, not
  reimplemented.

## Capabilities

### New Capabilities

- `joint-classification`: functional taxonomy (`motion` x `reversible` + `carries`)
  exposed as inventory metadata and schema-validated, so a joint can be chosen by
  intent.
- `finger-joint`: matched interlocking comb pair for strength-splitting + gluing.
- `mortise-tenon-joint`: rectangular keyed peg + pocket pair.
- `ball-joint`: spherical stud + slotted snap-in socket for multi-axis articulation.
- `hinge-joint`: interleaved knuckle leaves, separate-pin and print-in-place.
- `dowel-pin-joint`: cylindrical pin + bore with fit-selectable clearance.

### Modified Capabilities

- `dovetail-joint`: refactored onto the shared extrude-profile core (behaviour
  unchanged) and annotated with the new `motion`/`reversible`/`carries` metadata.

## Impact

- `blocks/joints.py` (five new mechanisms; private cores; dovetail refactor)
- `blocks/inventory.json` (new entries + metadata on existing dovetail entries)
- `blocks/inventory_schema.json` (three new optional fields; interface enum additions)
- `blocks/__init__.py` (export new functions)
- `tests/test_blocks.py` (geometry + clearance-relationship tests per pair)
- Consumers: any assembly script that splits a model for strength or builds a folding/
  articulating/keyed assembly.
