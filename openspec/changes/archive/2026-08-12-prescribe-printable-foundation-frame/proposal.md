## Why

`prompts/part.md` already recommends authoring a part with its physical bottom at
script Z=0 as a general, non-binding suggestion. It does not name the specific case
this pattern actually solves: a part whose assembled/world-frame position has its
physical bottom off the Z=0 plane (a "floating" part, e.g. bottom at Z=-2), where
authoring at a floating offset makes bottom-referenced dimensions (heights,
`centered=(True, True, False)` boxes, teardrop/boss Z placement) awkward to reason
about. The C5 Phone-Holder plate script solved this by authoring bottom-at-Z=0 and
reporting a `placement.translate_mm` offset (contract rule 6) to land in the true
assembled position -- but per its own `planning_notes`, the pattern was
"discovered/adopted during the build," i.e. arrived at only after the author had
already fought the floating frame once. Nothing today tells a part author facing a
floating assembled frame to reach for this pattern up front.

## What Changes

- `prompts/part.md`'s authoring-frame guidance gains one sentence naming the floating-
  assembled-frame case explicitly and pointing at the existing mechanism: author with
  the physical bottom at script Z=0, then report the offset as `placement.translate_mm`
  (contract rule 6) to land in the stated pose intent. This stays a recommendation, not
  a precondition -- consistent with `part-authoring-guidance`'s existing "the authoring
  frame is the author's choice" requirement -- so an author who prefers a different
  frame for a floating part is still not incorrect.
- No new mechanism, contract rule, or schema field: `placement.translate_mm` (contract
  rule 6, `src/placement.py`) and the Z=0-bottom recommendation both already exist. This
  change only makes the pairing explicit for the case that motivated it, so a future
  session doesn't have to rediscover the pattern by hand the way the C5 build did.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `part-authoring-guidance`: the existing "authoring frame is the author's choice"
  requirement's example guidance is extended with a named floating-assembled-frame case
  and the `translate_mm` write-back it pairs with, still stated as a recommendation.

## Impact

- `prompts/part.md`: one to two additional sentences in the "Coordinate vocabulary"
  section (around the existing Z=0-bottom recommendation).
- `openspec/specs/part-authoring-guidance/spec.md`: delta spec updating the affected
  scenario/example text.
- No code, schema, or test changes -- this is prompt/spec guidance only.
