## Why

The C5 Phone-Holder retrospective (`TODO.md` "skill improvements" item) found rounds
5-6 were both instances of the same geometric mistake, derived by the user rather
than gotten right by the LLM: for a flat face to fold flush against a target plane
at exactly +-90deg, the pivot axis must stand off the folding face's plane by
exactly the axis's perpendicular distance to the target plane. The rule and its
vocabulary (clevis/tongue/standoff) currently live only in that project's
`build/cradle.py` comments and the user's derivation -- nowhere in this repo's
`reference/` -- so the next hinge part will hit the same two correction rounds
instead of getting the placement right the first time.

## What Changes

- Add a "Flush-Fold Hinge Placement" section to `reference/FDM 3D Print Design
  Guidelines.md` (or a standalone `reference/hinge_flush_fold.md`, decided in
  design.md) deriving the standoff rule with the clevis/tongue/standoff vocabulary
  and a worked numeric example.
- Extend the reference-injection rule so a part using `pin_hinge`/`living_hinge`
  blocks, or named as `moving_union` in the plan's top-level `kinematics` array,
  additionally cites/receives this section -- the same conditional pattern
  `emboss_text.md` already uses for text/emboss parts.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `reference-injection`: add a hinge-part conditional citation/injection rule for
  the new flush-fold placement content, mirroring the existing text/emboss rule.

## Impact

- `reference/` (new or extended file)
- Part-prompt rendering (`prompts/part.md` substitution logic wherever
  `{{CQ_REFERENCE}}`/reference selection is implemented)
- No schema, runtime, or gate changes -- documentation/prompt-injection only.
