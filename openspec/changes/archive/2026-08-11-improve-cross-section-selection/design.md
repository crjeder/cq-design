## Context

`render_preview._section_cuts` already supports repeatable `--extra-section
axis=pos_mm` cuts that replace the bbox-centerline fallback (`preview-cross-sections`
spec). The plumbing from `run_cadquery_model.py` down to the renderer is done. The gap
is entirely upstream: `skill/phase3_build.md` Step 3 tells the human/agent authoring a
part to add `--extra-section` cuts only when they judge it necessary ("if this part
unions a feature into a body that already has a cavity..."), and that judgement call
gets skipped under time pressure, so the fallback (three bbox-centerline cuts) fires on
most real parts -- on a hollow box, guaranteed to show only air.

The same part-authoring step already builds a `--callout "name=...;center=..."` list
from every `interfaces[]` entry that has both `name` and `position_mm`
(`preview-feature-callouts`). That list is the exact set of candidate cut positions;
this change reuses it rather than introducing a second feature-enumeration path.

`request_log` entries are free-form prose (`text`) tagged with a `kind`
(`initial`/`clarification`/`correction`), append-only, so array order is chronological.
`src/request_log_search.py` does case-insensitive substring search against `text`,
optionally filtered by `kind`. Since `add-interface-name-field` shipped, an
interface's `name` (e.g. `ear_standoff`) is the same token a human or the planner would
plausibly use in `request_log.text` ("the ear standoff sits too low"), so a substring
match is a legitimate (if imperfect) join -- not a new NLP capability.

## Goals / Non-Goals

**Goals:**
- Make every part-authoring pass emit `--extra-section` cuts through the interfaces
  that matter most, without the author having to make a judgement call.
- Rank cuts using the user's stated priority: clarification-flagged features, then
  correction-flagged features, then everything else, most-recent first within a tier.
- Cap the cut count so previews stay reviewable regardless of part complexity.
- Keep the join mechanism cheap (a `request_log_search.py` call per candidate name, or
  one pass over an already-fetched `request_log`), not a new index or schema field.

**Non-Goals:**
- No change to `render_preview.py`/`run_cadquery_model.py`/`_section_cuts` internals --
  the `--extra-section` mechanism is correct and untouched.
- No new schema field. `interfaces[].name` already exists; `request_log.kind` already
  exists. This change is pure selection policy in the authoring procedure.
- No fuzzy/semantic matching between `request_log.text` and interface names --
  substring match only, same as `request_log_search.py` already does elsewhere in the
  pipeline (`request-log-search` spec).
- No change to the axis-choice mechanics beyond documenting a deterministic default
  (see Decisions) -- not building a general "best cutting plane" solver.

## Decisions

**D1. Where selection logic lives: authoring procedure text, not a new script.**
`skill/phase3_build.md` Step 3 already computes the `--callout` list by iterating
`interfaces[]`. The ranking/cap logic is a small, deterministic sort over that same
list plus a `request_log_search.py <name>` lookup per candidate -- cheap enough to be a
described procedure the orchestrator follows, not worth a dedicated `src/` tool.
Alternative considered: a `select_sections.py` script taking `BUILD_PLAN.json` +
`part_id` and emitting the `--extra-section` args. Rejected for now -- the logic is a
sort plus a handful of substring calls, and a new script means a new tested contract
for something that changes if the priority order is ever revisited by the user. If
this logic grows (e.g. real NLP matching later), promote it then.

**D2. Priority tiers and tie-breaking.**
Tier 1: interfaces whose `name` matches a `request_log` entry with `kind:
clarification`. Tier 2: matches a `kind: correction` entry. Tier 3: all other
named+positioned interfaces (no match, or only matches `kind: initial`). Within a tier,
order by the matching `request_log` entry's array position, descending (most recent
first) -- `request_log` is append-only so this is free. Interfaces in tier 3 (no
match) keep plan declaration order, after all matched tier-3 entries... actually: tier
3 has no request_log ordering signal, so plan declaration order is the only available
signal there.

**D3. Cap.**
Fixed cap of 3, matching the existing fallback's cut count (`preview-cross-sections`:
"three bbox-center cuts (Section X, Section Y, Section Z)"). This keeps output volume
predictable for review regardless of interface count; raising it is a one-line change
in `phase3_build.md` if a real session shows 3 is too few, not gated on this change.
Open question in TODO.md ("is 6 useful or noise") is deliberately left unresolved here
-- ship the conservative cap, revisit with usage data.

**D4. Axis choice per cut.**
Each interface's `position_mm` is a point; `_section_cuts`/`--extra-section` cuts
along a single axis at a value. Default: cut along the axis normal to the interface's
declared `wall` field when present (a `wall: "+x"`/`"-y"`/etc-style face normal already
carries the intended viewing direction -- cutting perpendicular to the wall shows the
feature face-on). When no `wall` is declared, fall back to the axis of
`position_mm`'s largest-magnitude component relative to the part bbox center (the
component most likely to be the feature's distinguishing coordinate). This is a
deterministic default, not a search over all three axes, to keep the cut count == the
interface count (before capping), not 3x it.

**D5. Matching mechanism: substring via `request_log_search.py`, not manual scan.**
Reuses the existing tool (`request-log-search` spec) rather than the orchestrator
re-reading `request_log` into context. One call per candidate `name`:
`request_log_search.py BUILD_PLAN.json --query "<name>"`, then inspect the returned
entries' `kind` values for the highest-priority match.

## Risks / Trade-offs

- [Substring match is imprecise -- an interface named `boss` could match unrelated
  prose containing "boss"] → Acceptable false-positive rate for a *ranking* heuristic
  (worst case: a cut gets bumped up in priority it didn't strictly earn, not a
  correctness bug -- the cut is still through a real interface). Revisit if sessions
  show this misranking in practice.
- [Cap of 3 may hide a genuinely important feature ranked 4th] → D3 explicitly leaves
  this open; cheap to bump later, and tier ordering means the 3 shown are the
  highest-priority ones by the user's own stated ranking.
- [Axis-normal-to-`wall` heuristic doesn't apply to interfaces without a `wall` field,
  and the magnitude fallback can pick a non-obvious axis for a near-diagonal position]
  → documented fallback in D4; author can still override by hand-adding
  `--extra-section` if the auto-picked axis misses the feature (mechanism unchanged,
  this is additive guidance not a hard constraint).
- [Procedure text (not code) means no automated enforcement -- an agent under time
  pressure could still skip it like it skips the current conditional] → this is the
  same risk the current conditional already has; making it an unconditional numbered
  rule (rather than a judgement call) is the mitigation the proposal targets, not a
  complete fix. Escalate to a script (D1 alternative) if procedure-text compliance
  proves insufficient.

## Migration Plan

Doc-only change (`skill/phase3_build.md`), no code/schema migration. Takes effect for
the next part-authoring session that reads Step 3. No rollback concerns beyond
reverting the doc edit.

## Open Questions

- Should the cap (D3) vary with interface count (e.g. proportional) rather than fixed
  at 3? Deferred pending real multi-correction-round usage data.
- Should tier 3 (unmatched interfaces) be cut at all once tiers 1+2 already reach the
  cap, or always guarantee at least one "everything else" cut per the user's stated
  three-bucket priority? Current design: tiers are exhausted in order up to the cap,
  so tier 3 only appears if tiers 1-2 together are under 3 -- matches "in that priority
  order" from the TODO literally, but could starve tier 3 entirely on a
  correction-heavy part. Revisit if that turns out to be undesirable in practice.
