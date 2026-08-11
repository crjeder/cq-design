## Context

The C5 Phone-Holder cradle/plate hinge (rounds 5-6) needed the pivot axis offset
from the folding face by exactly the axis's perpendicular distance to the target
plane, for the fold to close flush at +-90deg. The part author derived this twice
by hand (the user corrected round 5's placement, then round 6 re-derived
`EAR_STANDOFF = PIVOT_Y = 5mm` from scratch) because nothing in `reference/` states
the rule. The hinge in that project was block-free (raw clevis/tongue primitives,
per `blockless-kinematics`), so the trigger for citing this content can't rely on
`blocks_needed` alone -- `pin_hinge`/`living_hinge` block usage is the common case
but not the only one.

`reference/Engineering Design Rules.md` already exists as a tag-filtered, numeric-
only doc consumed via `{{ENGINEERING_RULES}}`, with an established "additionally
select when the part declares X" escape hatch (used today for `load`). This change
reuses both rather than adding a new file or a new placeholder.

## Goals / Non-Goals

**Goals:**
- Capture the flush-fold standoff rule (formula + one-line derivation +
  clevis/tongue/standoff vocabulary + the C5 cradle numeric example) in
  `reference/Engineering Design Rules.md`.
- Make it reach part prompts for both block-based hinges (`pin_hinge`,
  `living_hinge`) and block-free hinges (any part named as `moving_union` in the
  plan's top-level `kinematics` array), in both inline and cold-context rendering
  modes.

**Non-Goals:**
- No new reference file, no new `{{...}}` placeholder, no change to the FDM
  guidelines doc (that doc is prose-guideline oriented; this rule is a numeric
  formula, so it belongs in the Engineering doc per that doc's own scope line).
- No change to `plan_validate.py`, `cq_verify.py`, or any runtime check -- this is
  prompt-injection content only, not an enforced gate.
- No re-derivation of the C5 hinge's currently-built geometry (round 8 superseded
  the round-6 standoff with a different, non-fixed-angle stop; this reference
  doc captures the general rule, not a redo of that specific part).

## Decisions

**D1 -- New section in `Engineering Design Rules.md`, not a standalone file.**
Alternative considered: a dedicated `reference/hinge_flush_fold.md` cited the way
`emboss_text.md` is cited for text parts. Rejected: that would need a new
placeholder or a special-cased addition to `{{CQ_REFERENCE}}`'s substitution logic,
duplicating machinery `{{ENGINEERING_RULES}}` already provides. The content is a
numeric geometric formula (standoff distance = perpendicular distance), matching
the Engineering doc's own scope ("material constants, snap-fit formula
coefficients, rib/boss/gusset ratio limits ... no prose tutorials") better than the
FDM guide's prose-guideline sections anyway.

**D2 -- Selection trigger: `applies_to: pin_hinge, living_hinge` plus an
additional-selection rule for any part named as `moving_union` in the plan's
`kinematics` array.** Mirrors the existing `load` special case in the
reference-injection spec verbatim ("SHALL additionally select all load-relevant
sections when the part declares a plan `load`") -- same shape, new field.
`kinematics` is a plan-level array whose entries reference a part via
`moving_union` (not a per-part field), so the trigger is "this part id appears as
some entry's `moving_union`," which covers the block-free case
(`blockless-kinematics` entries omit `block`, not the plan-level array) without
inventing a new tag vocabulary. A part named in no `kinematics` entry and with no
matching `blocks_needed` gets no hinge content, same as today.

**D3 -- Keep the derivation to one short paragraph + formula table, not a full
proof.** The `Engineering Design Rules.md` preamble states "no prose tutorials."
The rotation-matrix justification is a couple of lines (why the standoff equals
the perpendicular distance, not a full trig derivation) -- enough for the author to
apply the formula and sanity-check it, not a tutorial.

## Risks / Trade-offs

- [Risk] Folding the rule into `Engineering Design Rules.md` under
  `blocks_needed`-based tags misses a block-free hinge whose plan also omits a
  `kinematics` entry naming it (shouldn't happen per schema, since a moving hinge
  without `kinematics` fails `plan_validate.py`'s joint-contract checks) ->
  Mitigation: none needed; that state is already invalid.
- [Risk] The rule only covers the exact +-90deg flush-fold case (a right-angle
  fold), not arbitrary fold angles -> Mitigation: state the scope explicitly in
  the new section so the author knows when the formula doesn't apply, rather than
  generalizing the formula speculatively.

## Open Questions

None -- scope is narrow enough (one reference section + one selection-rule
sentence) that no further decisions block implementation.
