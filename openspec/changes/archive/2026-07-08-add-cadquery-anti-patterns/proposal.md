## Why

The part prompt injects `reference/CadQuery Pattern Reference.md` as positive-space
guidance ("here is how to do X") but carries no negative-space catalog of the mistakes
LLMs actually make generating CadQuery. The maintainer-authored
[jmwright/cadquery-llm-skill](https://github.com/jmwright/cadquery-llm-skill) publishes
exactly that -- `patterns/anti-patterns.md` (14 items) and `patterns/common-patterns.md`
-- and is already tracked as upgrade material (`README.md` line 176, `TODO.md` line 138).

Two constraints shape how it lands:

1. **The pipeline is fluent-API only.** No block, exporter, or generated `result` uses
   the Free Function API (`cadquery.func`); `units.resolve_unions` keys on `cq.Workplane`.
   The func-API half of `common-patterns.md` (and the two func-specific anti-patterns)
   would teach an API the pipeline cannot consume -- it is dropped.
2. **A future build123d migration is plausible.** build123d is the same OCCT/BRep kernel
   with a different API surface. Roughly 30% of the anti-pattern material is kernel-level
   (portable to build123d unchanged); ~70% is fluent-API-specific, and most of that is the
   stateful-context bug class that build123d's algebra mode designs out entirely. Filing
   the catalog by durability now makes an eventual migration a mechanical section-swap.

## What Changes

- **Add `reference/CadQuery Anti-Patterns.md`** -- a negative-space companion to the
  pattern reference, organized into three durability tiers:
  - **Tier 1 -- Kernel-level (OCCT):** `BREP_API command not done` (fillet radius vs edge,
    self-intersecting profile/sweep, shell thickness vs curvature), boolean-in-a-loop,
    unclosed wires, feature-ops-vs-booleans principle. Portable to any OCCT API.
  - **Tier 2 -- Stateful-context footguns:** origin drift / `ProjectedOrigin`, losing solid
    context after a selector (`.end()`), `.val()` vs `.vals()`, `.each()` misuse,
    `.translate()` on a Workplane, index-selector fragility, hardcoded global coords.
    Deleted outright under an algebra-mode API.
  - **Tier 3 -- CadQuery API mechanics:** `combine=False` on `.extrude()`, `.cutBlind()`
    normal direction / `invert=True`, fluent-vs-func mixing.
- **Reconcile three contradictions** the new material would otherwise create with the
  existing reference, anchored on one skill rule: *feature ops for bosses/holes/edges;
  booleans for combining separate solids and for cavities/enclosures where `.shell()` is
  fragile* (matches `hollow_box` and Common Gotcha #10). The other two: `.translate()` is
  valid on an extracted Shape / final result, not as a mid-chain positioning primitive
  (vs. Transform Operations); the Fresh Workplane Pattern still uses a workplane frame and
  does not contradict the "don't hardcode globals" anti-pattern (cross-reference, not
  duplicate).
- **Fold the surviving fluent recipes into the main pattern reference** as positive-space
  how-tos: `.placeSketch()` reusable profile, `.extrude(combine=False)`, and
  `.cutBlind()` with `workplane(invert=True)`. These appear as recipes in the pattern
  reference and as footguns in the companion (different cognitive modes, intentional).
- **Always-inject the companion.** Unlike `emboss_text.md` (text parts only), anti-patterns
  apply to every part, so the companion is appended to `{{CQ_REFERENCE}}` unconditionally,
  before the conditional `emboss_text.md`.
- **Leave the existing "Workplane Context Stacking" and "Fresh Workplane Pattern" sections
  in the main reference**, cross-referenced from the companion's Tier 2. Physically
  relocating them is migration-prep for a migration that may not happen and churns a
  load-bearing, cross-referenced file; the cross-reference gives the same "these are the
  deletable ones" signal without the churn.

## Capabilities

### Modified Capabilities
- `reference-injection`: part prompts additionally receive `reference/CadQuery
  Anti-Patterns.md`, appended to the pattern reference unconditionally (before the
  text-only `emboss_text.md`).

## Impact

- Reference: `reference/CadQuery Anti-Patterns.md` (new), `reference/CadQuery Pattern
  Reference.md` (three fluent additions + three reconciliations + ToC entry).
- Docs: `SKILL.md` (Setup reference list line ~389, `{{CQ_REFERENCE}}` row line ~430,
  key-files table line ~1075), `README.md` line 176 / `TODO.md` line 138 (mark done).
- No Python or test changes: injection is Claude-driven inline (SKILL.md Part loop
  Step 1), not a rendering function.
- Content-independent of the in-progress `placement-supersedes-assembly` change; both edit
  the `reference-injection` spec, so land order matters for the delta but not for behavior.
- Explicitly **out of scope**: the Free Function API (`cadquery.func`) content, and any
  build123d migration -- the tier structure only *prepares* for one.
