## Why

`teardrop_bore` makes the roof of a HORIZONTAL hole self-supporting, but there is
no counterpart for a HORIZONTAL solid cylinder (a peg, pin, or boss protruding in
the build plane). The underside of such a cylinder is an unsupported overhang that
sags or needs support material. Authors currently have no block to produce a
printable horizontal peg, so they either accept support scars or avoid the feature.

## What Changes

- Add a `teardrop_post(d, length, angle=45, flat=1.2)` additive block in
  `blocks/connectors.py`: a horizontal solid cylinder whose lower half is replaced
  by two 45-degree faces meeting in a narrow flat bottom, so the underside
  self-supports when printed in the modeled orientation (apex/flat pointing down).
- Factor the shared cross-section into a `_drop_profile(r, angle, apex)` helper.
  `teardrop_bore` is refactored to consume it with `apex="up"` and its output stays
  byte-for-byte unchanged; `teardrop_post` consumes it with `apex="down"` plus flat
  truncation.
- Small-feature handling is advisory, never fatal: the block clamps `flat` so the
  inclined faces always exist and always builds; it emits `warnings.warn` when `d`
  is below the useful threshold (~3 mm). The planner-facing guidance (minimum
  diameter, and the redirect to a 45-degree-rotated cube for functional peg/hole
  pairs) lives in the inventory `use` string.
- Register `teardrop_post` in `blocks/inventory.json` and re-export it from the
  `blocks` package.
- Add a "self-supporting horizontal features" note to the reference docs / planning
  prompt covering the three-way choice: `teardrop_bore` (hole roof), `teardrop_post`
  (free peg underside), and a rotated cube (functional peg/socket pair).

## Capabilities

### New Capabilities
- `teardrop-post`: a self-supporting horizontal solid cylinder (peg/pin/boss) block
  whose lower half is replaced by 45-degree faces and a narrow flat bottom, with
  advisory small-feature handling.

### Modified Capabilities
- `block-library`: the required-inventory enumeration and presence scenarios gain
  `teardrop_post` (registered in `blocks.connectors`).

## Impact

- Code: `src/blocks/connectors.py` (new function + shared `_drop_profile` helper;
  `teardrop_bore` refactored without behavior change), `src/blocks/__init__.py`
  (re-export), `src/blocks/inventory.json` (new descriptor).
- Docs: `reference/` and `prompts/planning.md` gain the self-supporting-features note.
- Tests: `tests/test_blocks.py` gains coverage for `teardrop_post` and the
  unchanged `teardrop_bore` output.
- No changes to the `run_cadquery_model.py` JSON contract; the advisory surfaces via
  the existing `stderr` field and the inventory `use` string. Additive block, so the
  subtractive-epsilon requirement does not apply.
