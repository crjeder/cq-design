## Why

`pin_hinge` builds a print-in-place hinge as two rigid leaves that pivot about a filament pin, but it
returns them **fused into one `cq.Workplane`**. `model_export` then collapses that into a single
union, so the hinge's own motion -- leaf A rotating against leaf B -- is a frozen blob the kinematic
check can never sweep. The check we shipped (`single-axis-joint-contract`) can validate a joint's
range against the rest of the model, but a print-in-place hinge's two leaves are invisible to it
because they are one body.

Separately, the inventory still ships `hinge_leaf`: a **lone-half** hinge (one leaf per call) whose
two halves are authored by two independent calls. Per the `joint-contract` design (D3), that is the
matched-pair anti-pattern -- nothing binds the two halves to one parametric source, so they can drift
apart until they no longer mate. `pin_hinge` already carries both matched leaves; `hinge_leaf` is the
footgun to retire.

## What Changes

- **`pin_hinge` returns two member unions.** It SHALL return a `dict[str, cq.Workplane]`
  `{"leaf_a": ..., "leaf_b": ...}` -- the two leaves as separate named bodies (each with the coaxial
  bore) -- instead of one fused `cq.Workplane`. The leaves are already geometrically disjoint
  (interleaved knuckles do not fuse), so this is a return-shape change, not a geometry change. This
  rides the shipped multi-union machinery: a print-in-place hinge part declares `unions:
  [{"id": "leaf_a"}, {"id": "leaf_b"}]` and its script returns the dict, so `model_export` emits two
  unions and the kinematic check can sweep `leaf_a` against `leaf_b`. **BREAKING** for any script
  that treats `pin_hinge(...)` as a single `Workplane`.
- **Retire `hinge_leaf`.** Remove the lone-half `hinge_leaf` function, its `blocks` re-export, and its
  `inventory.json` entry. **BREAKING**: the separate-parts (two independently printed leaves) hinge
  it enabled is withdrawn; it returns properly once the cross-part kinematic tree can distribute
  `pin_hinge`'s two members onto two parts. Print-in-place hinges (the common case) are fully covered
  by `pin_hinge`.
- **Correct the stale `pin-hinge` dof example.** The `pin-hinge` spec still shows the pre-reshape
  `dof` (`{type, axis: Y, mechanical_limit, unit}`); update it to the shipped vector model
  (`direction`/`origin`, unit derived) so the spec matches `main`.

## Capabilities

### Modified Capabilities
- `pin-hinge`: `pin_hinge` returns the two leaves as a named `{leaf_a, leaf_b}` multi-union dict
  (not one fused body), so a print-in-place hinge's leaves are separate unions the kinematic check can
  sweep; the dof example is corrected to the vector model.
- `joint-classification`: the taxonomy's hinge example no longer references the retired `hinge_leaf`
  (it uses a surviving hinge block).

### Removed Capabilities
- `hinge-joint`: the `hinge_leaf` lone-half factory is removed (matched-pair anti-pattern; superseded
  by `pin_hinge`'s built-in matched pair).

## Impact

- Blocks: `src/blocks/joints.py` (`pin_hinge` return shape; delete `hinge_leaf`),
  `src/blocks/__init__.py` (drop the `hinge_leaf` re-export), `src/blocks/inventory.json` (reshape the
  `pin_hinge` descriptor to note its two unions; remove the `hinge_leaf` entry).
- Guidance: `prompts/planning.md` (drop the `hinge_leaf` reference; a `pin_hinge` part declares two
  unions).
- Tests: `tests/test_blocks.py` (`pin_hinge` returns a two-key dict of watertight leaves; `hinge_leaf`
  is gone), and a kinematic-check test that a print-in-place `pin_hinge`'s `leaf_a` sweeps against
  `leaf_b`.
- Specs: `pin-hinge` (return shape + dof example), `joint-classification` (hinge example), and the
  removed `hinge-joint`.
- Out of scope: dovetail/ball matched-pair merges, the `union` interface fuse pad, `parameters.py`,
  and the cross-part kinematic tree -- all deferred to the tree slice, which is what makes cross-part
  matched pairs (and the separate-parts hinge) real again.
