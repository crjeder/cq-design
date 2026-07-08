# Design

## Context

Two source files from `jmwright/cadquery-llm-skill` are candidate additions to the
injected reference corpus: `patterns/anti-patterns.md` (14 items) and
`patterns/common-patterns.md` (fluent + Free Function recipes). The corpus is injected
whole into every part prompt via `{{CQ_REFERENCE}}`, so token cost and internal
consistency both matter, and any CadQuery-specific knowledge is migration debt against a
possible future move to build123d (same OCCT kernel, different API).

## Decision 1 -- Drop the Free Function API entirely

The pipeline is fluent-API by construction: every block returns a `cq.Workplane`, and
`units.resolve_unions` accepts only a `Workplane` or `dict[str, Workplane]`. A func-API
`result` is a bare `Shape` and would fail that contract.

Considered keeping it for its build123d affinity (CadQuery func ~ build123d algebra mode).
Rejected: you would migrate to *build123d algebra*, not *cadquery.func* -- they are
conceptual cousins but syntactically distinct, so cadquery-func content is neither present-
usable nor a portable asset. Keeping it would also force two authoring styles in a corpus
the pipeline consumes in exactly one. Consequence: anti-patterns #11 (fluent-vs-func) is
kept only as a one-line "don't mix" note; #13 (boolean-in-a-loop) is kept as a kernel truth
with the fix expressed in fluent + compound form (matching the existing "Non-Overlapping
Part Assembly" section).

## Decision 2 -- Companion file, not merged into Common Gotchas

The pattern reference's "Common Gotchas" is already 12 items; folding ~8 survivors makes it
20 and blurs positive-space how-tos with negative-space "you did X wrong." A separate
`CadQuery Anti-Patterns.md` mirrors the established `emboss_text.md` split (addressable by
name, injected as a unit) and keeps the negative-space genre distinct. Unlike `emboss_text`,
it is injected **unconditionally** -- anti-patterns apply to every part.

## Decision 3 -- Three durability tiers

The companion is organized by how the material survives a build123d migration, because that
sorting is also a semantically real sort (kernel geometry constraints vs. artifacts of a
stateful API):

| Tier | Nature | build123d fate | Items |
|------|--------|----------------|-------|
| 1 Kernel-level (OCCT) | Real geometry constraints | Portable, either mode | #1(principle), #12, #13, #14 |
| 2 Stateful-context | Bugs caused by persistent origin + selection stack | **Deleted** under algebra mode | #2, #3, #6, #7, #8, #9, #10 |
| 3 API mechanics | CadQuery method-specific semantics | Rewrite to build123d equivalent | #4, #5, #11 |

A future migration keeps Tier 1 verbatim, deletes Tier 2, and rewrites Tier 3 -- a
mechanical section-swap rather than a re-read of the whole file.

Note on #10 (index-selector fragility): the fragility principle is broader than fluent
(build123d `sort_by()[1]` shifts too), but the tag-based fix is fluent-specific, so it sits
in Tier 2 with a note.

## Decision 4 -- Reconcile three contradictions in the main reference

Pasting the anti-patterns verbatim makes the injected corpus argue with itself. Each is
resolved by scoping, anchored on the boolean rule:

1. **Anti-pattern #1 (feature ops > booleans) vs. Common Gotcha #10 (prefer boolean-cut over
   `.shell()` for enclosures).** Both true at different scopes. Anchor rule: *feature ops for
   bosses / holes / edges; booleans for combining separate solids and for cavities /
   enclosures where `.shell()` is fragile.* This is exactly what `hollow_box` does
   (`src/blocks/primitives.py`). Added to Tier 1 as the boolean-usage rule; Gotcha #10 gets a
   back-reference.
2. **Anti-pattern #2 (`.translate()` bypasses the workplane frame) vs. Transform Operations
   (`part.translate((dx,dy,dz))` shown as normal).** Scope note: `.translate()` is valid on an
   extracted Shape or a finished `result`; it is not a mid-chain positioning primitive.
3. **Anti-pattern #3 (don't hardcode global coords) vs. the Fresh Workplane Pattern (endorses
   `transformed(offset=...)` placement).** No real conflict -- Fresh Workplane still uses a
   workplane frame. Companion cross-references the pattern rather than restating it.

## Decision 5 -- Fold surviving fluent recipes into the main reference

`.placeSketch()`, `.extrude(combine=False)`, and `.cutBlind()` + `workplane(invert=True)`
are genuinely new positive-space recipes and belong in the pattern reference next to the
operations they extend (Sketch API / Machining Operations). `combine=False` and the
`cutBlind` direction also appear as footguns in the companion (Tier 3). The intentional
duplication serves two cognitive modes: "how do I" (reference) vs. "why did my model break"
(companion).

## Decision 6 -- Do not relocate existing stateful-context sections

"Workplane Context Stacking (Origin Drift)" and "The Fresh Workplane Pattern" are Tier-2
material by nature, but they stay in the main reference. Moving them into the companion is
migration-prep for a migration that may never happen, churns a heavily cross-referenced file
(Gotcha #7 and `emboss_text.md` both point at them), and buys only tidier future deletion.
The companion cross-references them instead, preserving the "these are the deletable ones"
signal at no churn.

## Out of scope

- The Free Function API content (Decision 1).
- Any actual build123d migration -- the tier structure only prepares for one.
- Token-budget reduction of the existing reference; this change adds a companion, it does
  not trim the base.
