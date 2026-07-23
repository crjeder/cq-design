## Context

`src/cq_verify.py` already catches three silent CadQuery failure modes at construction
time, all via cheap bounding-box/volume comparisons rather than exact BRep queries:
`verify_boolean` (no-op cut/union), `verify_feature_bounds` (feature pokes past the base
body on any axis), `check_workplane` (origin drift after `.center()`/`.hole()`).

None of these catch the observed bug class: a feature (e.g. a standoff post) is
positioned using a coordinate that is legitimately a *centerline* for one purpose (the
pivot axis a knuckle is centered on) but gets reused, unadjusted, as a *boundary* for an
adjacent feature (the leg that must reach the standoff's far face) -- off by exactly
half the standoff's thickness. `verify_feature_bounds` cannot catch this directly: in the
real case (`build/cradle.py`, ROUND 5-7 comments), the standoff's overflow past the leg's
bbox on Z was *intentional* (a post rising off its base) while the overflow on Y was the
actual defect (only half the post's footprint sat on the leg) -- an all-axis check can't
separate the two.

A prior exploratory design (`openspec/changes/archive/2026-07-01-joint-contract/design.md:412-421`)
named the general rule for the *inter-union* joint case: a mating area "MUST be touched
by a to-print object in its own union... realized by real material, not floating." That
design was never implemented and stays blocked on cruxes (satisfaction algebra, sub-body
naming) specific to blocks emitting multiple mated unions. This change reuses the same
vocabulary ("mating area", "backed by material") one level down -- between two features
inside a single part script, before a block or union model is even in play.

## Goals / Non-Goals

**Goals:**
- Catch "feature only partially backed by its intended neighbor" at construction time,
  in the same script, with the offending feature named in the error -- same philosophy as
  the existing three `cq_verify` assertions.
- Keep the check axis-aligned-bbox-based, consistent with the rest of the file (no new
  BRep-face-adjacency machinery, no new dependency).
- Make the declaration read as a stated design intent ("this face of X must be backed by
  Y"), not just a bbox diff bolted on after the fact -- so the author's attention lands on
  the contact requirement while writing the feature, not after.

**Non-Goals:**
- Exact BRep face-to-face contact/adjacency verification (e.g. detecting a cavity in the
  backer directly under the contact point). Bbox containment is an approximation, same
  class of approximation `verify_feature_bounds` already accepts.
- Arbitrary (non-axis-aligned) mating faces. Declaring a face by axis direction
  (`"+x"`/`"-x"`/`"+y"`/`"-y"`/`"+z"`/`"-z"`) covers every case seen so far (standoffs,
  bosses, ribs are all built axis-aligned in this pipeline's part scripts) and matches
  `car_box`/`.box()`-style construction, which is how virtually all scratch geometry in
  this codebase is authored.
- Reviving the inter-union / block-declared mating area from the archived design. That
  stays a separate, larger change with its own open cruxes (see Open Questions below,
  and the `TODO.md` note this change adds).
- Any `BUILD_PLAN.json` / `inventory.json` schema change. This is a script-level
  assertion only.

## Decisions

### `verify_backed(backer, feature, axis, label="", tolerance=0.1)`

Signature and contract mirror `verify_feature_bounds`: takes two solids (or Workplanes,
via the existing `_solid()` unwrap helper), returns `feature` unchanged on success, raises
a marked `RuntimeError` (`[cq-verify:unbacked_mate:<label>] ...`) on failure so
`run_cadquery_model.py` can map it to a typed `unbacked_mate` error the same way the
other three are mapped today.

`axis` names which face of `feature` is the mating face, as a signed axis token
(`"+x"`, `"-x"`, `"+y"`, `"-y"`, `"+z"`, `"-z"`) -- the direction from `feature`'s
interior toward `backer`. Algorithm, entirely on `BoundingBox()` values:

1. **Contact coordinate**: the feature's bbox extent on the named axis and side (e.g.
   `axis="-z"` -> `contact = bb_feature.zmin`, the feature's bottom face).
2. **Reach check**: `backer`'s bbox must extend at least to that coordinate from the
   opposite side (e.g. `bb_backer.zmax >= contact - tolerance`) -- the backer is actually
   present at the contact plane, not stopping short of it.
3. **Containment check** (the check that actually catches the observed bug): on the
   *other two* axes, `feature`'s bbox range must fall within `backer`'s bbox range at
   that plane, within `tolerance`. This is what flags a standoff whose footprint only
   half-overlaps its supporting leg -- the leg's Y-range not covering the standoff's
   Y-range is exactly a containment failure on the axis orthogonal to the declared
   contact normal.

Worked against the real historical bug (`axis="-z"`, `backer=leg`, `feature=standoff`,
pre-ROUND-7 dimensions): reach check passes (leg's top reaches the standoff's bottom);
containment check on Y fails (`standoff.ymax=6.0 > leg.ymax=5.0 + tolerance`) -- the
helper would have raised `unbacked_mate` naming the Y overflow, at the point the standoff
was authored, instead of requiring a human to notice a "brittle" joint after export.

**Alternative considered**: a per-axis variant of `verify_feature_bounds` itself (check
only the axes the caller names, skip others) rather than a new function. Rejected: that
still frames the check as "did this feature overflow its base," which is the wrong
question when the feature is *meant* to extend past the base on the contact-normal axis
(that's the entire reason for a standoff to exist). Naming a `backer` + `axis` instead of
reusing `before`/`after` on the same body also matches the actual authored intent more
directly -- `feature` and `backer` are two solids the author is about to `.union()`, not
one solid before/after a boolean.

**Alternative considered**: full 2D polygon footprint (as literally specified in the
archived design, `[pA, pB, pC, pD]`) instead of axis-aligned bbox containment. Rejected
for this change: no part script in this codebase currently authors a non-axis-aligned
mating face, and the bbox approach requires no new geometry-intersection code, staying
consistent with the rest of `cq_verify.py`. Revisit if a future part needs a non-box
contact face.

### Prompt guidance placement

Extends the existing "Construction-time verification" bullet list in `prompts/part.md`
(and mirrored generated-script rules in `SKILL.md`) rather than adding a new section --
same list that already tells the author when to reach for `verify_boolean` /
`check_workplane` / `verify_feature_bounds`. New bullet: declare `verify_backed` when a
feature (standoff, boss, rib, ear, gusset) must be fully supported by a *named
neighboring feature* at one specific face, as opposed to a feature that legitimately
extends past its base on other axes (which is the normal, non-mating case).

### `TODO.md` note

Adds a note under the existing line "design error: the llm often places the center of a
box where actually a wall should sit" (currently unresolved), pointing at this change and
recording the open crux explicitly: whether the intra-part `verify_backed` check
generalizes upward into the archived inter-union mating-area design (row 2 of that
design's printed/swept/checked classification table), or stays a deliberately separate,
narrower mechanism that only shares vocabulary. This is the "should feed back" requirement
-- captured as a pointer for whoever picks up the block-level design next, not resolved
here.

## Risks / Trade-offs

- **Bbox approximation can pass a false negative** (backer's bbox reaches the contact
  plane and contains the footprint, but the actual solid has a cavity right at the
  contact point) -> Mitigation: same accepted risk as `verify_feature_bounds` and
  `verify_boolean`'s centroid/volume signature; exact BRep contact-area verification is
  explicitly a non-goal, and can be revisited later without changing the call site if it
  proves insufficient.
- **Over-declaration adds noise** if authors wrap every feature-to-feature adjacency in
  `verify_backed`, mirroring the caution the existing guidance already states for
  `verify_boolean` ("do NOT wrap a boolean whose tool trivially overlaps the body") ->
  Mitigation: prompt guidance scopes it explicitly to "must be fully backed at a specific
  face," not general adjacency.
- **Two similarly-named mechanisms could diverge** (this intra-part check vs. the still-
  shelved inter-union mating area) if the later change reinvents its own vocabulary ->
  Mitigation: the `TODO.md` note captures the open question now, before a second
  implementation exists to reconcile against.

## Migration Plan

Purely additive: new function, new typed error kind, new prompt bullet, new `TODO.md`
note. No existing call sites, schemas, or generated scripts change behavior. Existing
part scripts that don't call `verify_backed` are unaffected; the assertion is opt-in per
the author's judgment, same as the three existing `cq_verify` helpers.

## Open Questions

- Does `verify_backed`'s bbox-containment approach need to compose with
  `verify_feature_bounds` (e.g. a combined call), or do they stay independent since they
  answer different questions (overall overflow vs. one-face backing)?
- Should the typed `unbacked_mate` error also report the specific axis/side that failed
  containment (analogous to `verify_feature_bounds`'s per-axis overflow report), or is
  naming the label enough given the caller already knows which axis they declared?
- Left to the future block-level revival (recorded in `TODO.md`, not resolved here): does
  `verify_backed` become the primitive the inter-union mating-area gate check is built on
  top of (applied to two unions' exported STLs instead of two in-script solids), or is
  that a genuinely different implementation once the satisfaction-algebra crux resolves?
