## Context

`prompts/part.md`'s "Coordinate vocabulary" section already carries a non-binding
recommendation: author a part's physical bottom at script Z=0, unless a different frame
is more natural (added by the `author-owned-placement` change). Contract rule 6 already
requires the author to report an assembled-frame transform (`rotate` + `translate_mm`,
same shape as `placement`) that carries the authored geometry into the stated pose
intent. Both pieces exist; nothing connects them for the case that actually motivates
the Z=0 recommendation -- a part whose assembled position floats off Z=0.

## Goals / Non-Goals

**Goals:**
- Name the floating-assembled-frame case explicitly in `prompts/part.md` so a part
  author facing it reaches for the existing Z=0-authoring + `translate_mm` write-back
  pattern without having to rediscover it through a correction round.
- Keep the guidance a recommendation, not a precondition, per
  `part-authoring-guidance`'s existing "authoring frame is the author's choice"
  requirement.

**Non-Goals:**
- No new contract rule, schema field, or mechanism. `translate_mm` and the Z=0
  recommendation both already ship.
- No change to `placement.py`, `plan_validate.py`, or any check/gate code.
- Not attempting to detect "floating" automatically from the plan -- this is prompt
  guidance for the author to apply at authoring time, same as the existing
  recommendation.

## Decisions

- **Extend the existing recommendation sentence rather than add a new section.** The
  Z=0-bottom recommendation is already exactly one sentence in "Coordinate vocabulary".
  Adding a standalone "Printable foundation" section would duplicate that guidance and
  risk the two drifting apart. One or two added sentences immediately following it
  keeps the pairing visible and easy to keep in sync.
- **State the case by its symptom (assembled position off Z=0), not by a named part
  archetype.** The C5 plate is one instance; the underlying trigger is any part whose
  stated pose intent puts its physical bottom away from Z=0 in the assembled frame,
  which is decidable from the pose intent, not from a part "type" the schema would need
  to add.
- **Leave `part-authoring-guidance`'s modal language unchanged.** The spec's own rule
  ("Modal language is reserved for checkable contracts") means this addition stays
  plain declarative prose, matching the existing recommendation's phrasing -- not a
  new SHALL/MUST, since departing from it is still not incorrect.

## Risks / Trade-offs

- [Risk: the added sentence reads as a second, competing recommendation next to the
  existing one] -> Mitigation: word it as a continuation ("this applies especially
  when...") rather than a separate rule, and keep both under the same bullet/paragraph.
- [Risk: none of this is enforced, so an author can still ignore it as before] ->
  Mitigation: accepted -- this is deliberately a recommendation per the existing spec
  requirement, not a new gate; enforcement was never in scope for the Z=0 guidance it
  extends.
