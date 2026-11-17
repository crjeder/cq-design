## Why

Slicer supports scar surfaces and are slicer-specific. Designed-in breakaway fins
(a thin wall standing off the part by a small gap, plus horizontal "tines" that fuse
into the part) live in the STL itself and print right on any printer. The
[support-fins](https://github.com/gittrahan/support-fins) project (MIT; geometry numbers
from Slant3D's published fin guidance) documents the geometry. Today cq-design only
*measures* overhangs (`quality_gate`, `print_orientation`) and can export an
`enable_support` flag to the slicer; it cannot author support geometry, so a part
printed in a strong (tipped) orientation always depends on slicer supports.

## What Changes

- Add a CadQuery block `breakaway_fin` (in a new `blocks/supports.py`, registered in
  `blocks/inventory.json`): a fin wall with 0.2 mm standoff, one-layer-high horizontal
  tines bridging the gap into the part, rounded top, optional bed-pad ellipse. Built in
  the part's build pose from explicit parameters (anchor point on the overhang, direction
  to the bed, height, layer height, nozzle width).
- Add `src/fin_placement.py`: reads the print-pose STL, finds overhang regions the gate
  already flags (`overhang_exceeded`), and emits a JSON list of suggested fin placements
  (anchor, height, wall length) that a part script can feed to the block. Advisory only;
  it never edits geometry and never picks the orientation.
- The quality gate runs the placement logic itself: when it flags an `overhang_exceeded` warning it adds a `fin_hint` info finding with the suggested fins. The user can opt out with `constraints.fin_hints: false` in `BUILD_PLAN.json`; the gate re-reads the plan on every run, so that entry needs no other carrying.
- Fins are authored as a separate union (`support_fins`) in the part's multi-union result,
  tagged as sacrificial, so the existing union machinery exports and previews them.
- Quality gate: a `designed_support` `info` finding when fins are present, and fin
  unions are excluded from `overhang_exceeded`, `sliver_fin`, thin-region and
  brim checks that would misread the deliberate 0.2 mm gap and tines.
- `estampo` export sets `enable_support: false` for parts that carry fins.
- Reference doc `reference/support_fins.md` records the dimension table and its
  provenance (Slant3D numbers via support-fins `FIN-SPEC.md`).

Not in scope: resin pin mode, sway braces for tall parts, gussets, STEP/OBJ import UI,
and automatic orientation changes (the user or `print_orientation` picks the pose).

## Capabilities

### New Capabilities
- `breakaway-support-fins`: fin block geometry (wall, standoff, tines, rounded top,
  bed pad), placement suggestion script, and sacrificial-union handling.

### Modified Capabilities
- `overhang-analysis`: sacrificial fin unions are excluded from overhang/sliver findings
  and a `designed_support` info finding is emitted.
- `block-library`: inventory gains the `breakaway_fin` descriptor.
- `estampo-export`: parts with fin unions export `enable_support: false`.

## Impact

- New: `src/blocks/supports.py`, `src/fin_placement.py`, `reference/support_fins.md`,
  tests (`tests/test_supports_block.py`, `tests/test_fin_placement.py`).
- Edited: `src/blocks/inventory.json`, `src/blocks/__init__.py`, `src/quality_gate.py`,
  `src/estampo_export.py`, `FILES.md`, `reference/scripts.md`, `TODO.md` (item removed
  when done).
- No new dependencies; geometry is CadQuery, analysis is trimesh/numpy already present.
- Fin dimensions are unverified on a physical printer; the reference doc states this.
