## Why

`blocks.teardrop_bore` / `teardrop_post` exist and are specced, but builders almost never use them: `prompts/part.md` and `SKILL.md` never tell a builder to prefer them for horizontal holes, and no gate notices a hand-rolled round horizontal hole. A prior run (tread-down stair step, printed flipped 180 deg about X) rejected teardrops on a wrong assumption: that the peak must point +Z in the model. The peak must point print-up, which there is assembly -Z; the run had to hand-roll the peak. `teardrop_bore` hardcodes a +Z peak and its docstring says the part must print in its modeled orientation, which invites that mistake. Result: roof overhangs in bores that print badly (TODO.md, Defects: "teardrop shaped holes not used").

## What Changes

- `blocks/connectors.py` + `inventory.json`: `teardrop_bore` gains `peak="up"|"down"` (default up, backward compatible) so a flipped print pose needs no hand-rolled profile; docstring/inventory `use` text drop the "must print in modeled orientation" wording.
- `prompts/part.md`: add a rule routing horizontal round holes/pegs (axis in the build plane at the chosen print pose), with the peak toward print-up, not necessarily model +Z to `teardrop_bore` / `teardrop_post`.
- `script_lint.py`: advisory finding when a part script cuts a round hole on a side-facing workplane (`XZ`/`YZ` or a `<X`/`>X`/`<Y`/`>Y` face) without `teardrop_bore` in the script.
- `quality_gate.py`: when `overhang_exceeded` is emitted, the hint names `teardrop_bore` instead of the generic "add chamfers".
- Tests for the lint rule and the hint.

## Capabilities

### New Capabilities
- `horizontal-hole-guidance`: builder prompt rule plus advisory lint/gate hint steering horizontal round holes to teardrop blocks.

### Modified Capabilities

## Impact

`prompts/part.md`, `src/script_lint.py`, `src/quality_gate.py`, `tests/test_script_lint.py`, `tests/test_quality_gate.py`. Advisory only; no schema or JSON-contract change.
