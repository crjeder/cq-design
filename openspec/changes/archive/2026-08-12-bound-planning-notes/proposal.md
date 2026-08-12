## Why

`planning_notes` has no stated purpose and no declared reader. `prompts/planning.md:39`
commissions it as "your reasoning: why you chose this decomposition, how you derived
dimensions, which sources you checked, and any design trade-offs" -- an unbounded
charter -- while no `{{PLANNING_NOTES}}` substitution exists in `prompts/part.md` and no
Phase 3 step reads it. The result is a large free-prose field that costs context every
time the plan is loaded and that nothing is told to consume or maintain.

An audit against two real projects (HitsterTower, C5 Phone-Holder, 2026-08-12, recorded
in `TODO.md`) asked what a re-planner would get wrong without the field that
`request_log` + `parts[]` did not already give it. The answer was not "nothing": three
categories of content are load-bearing only there. Everything else measured -- roughly
four fifths of C5's 5459-character field -- is either already banned by shipped rules or
is prose restating a structured field.

## What Changes

- Replace the unbounded charter sentence in `prompts/planning.md` with an **inclusion
  rule**: `planning_notes` carries only (a) decisions against something (a rejected
  alternative, an archetype, a schema mechanism, a user's literal request, a profile
  default, or a deliberately omitted field) with its reason, (b) invariants binding more
  than one part, which no per-part field can hold, and (c) the assembly procedure and
  the non-printed hardware it consumes. Content outside these three categories is
  excluded.
- Add a general **no-prose-restatement rule**: anything already expressed by a
  structured field (`placement`, `load`, `blocks_needed`, `dimensions`, `interfaces`,
  `intent`, `optimize_for`) must not be narrated in `planning_notes`. This generalizes
  the existing `placement`-only ban from `author-owned-placement` and closes the
  restatement of `load`/`blocks_needed`/`intent` observed in the C5 plan.
- Add a **re-plan consumption clause** alongside the existing `request_log`
  carry-forward instruction: a re-plan SHALL read `planning_notes` before re-deciding,
  SHALL NOT re-litigate a decision recorded there without saying so, and SHALL rewrite
  it to the current state (it is rewritten, never appended to).
- Update the `planning_notes` description in `src/build_plan_schema.json` to name the
  three categories, so the bound is visible at the schema where the current-state-only
  rule already lives. Description text only -- no type, no new property, no new
  constraint.
- Not in scope, filed as post-V1.0 items in `TODO.md`: moving provenance out of
  `planning_notes` into a structured field, structuring category (a) as
  `{considered, rejected_because}` entries, and the bill of non-printed materials. All
  three are schema changes and fall under the V1.0 feature freeze; this change is
  prompt, skill-doc, and schema-description text only.

## Capabilities

### New Capabilities

None. This bounds an existing field rather than introducing a capability.

### Modified Capabilities

- `planning-phase`: the existing "planning_notes and part_notes describe current state
  only" requirement is extended from a purely negative bound (no round-by-round history)
  to a positive inclusion rule naming the three categories the field carries, plus the
  no-prose-restatement rule and the re-plan consumption clause.

## Impact

- `prompts/planning.md` -- the charter sentence above the Rules section, and the rules
  covering notes content and re-plan behavior. Rule numbers 1-15 stay stable;
  `skill/phase2_planning.md` and `skill/phase3_build.md` cite them by number.
- `src/build_plan_schema.json` -- `planning_notes` description string only.
- `skill/phase2_planning.md` -- the passage contrasting `planning_notes` with the
  parameters block.
- `openspec/specs/planning-phase/spec.md` -- via the delta spec.
- No behavior change to any Python tool. `plan_validate.py` does not inspect the field's
  content and is unaffected; `test_plan_validate.py` and `test_eval_corpus.py` must stay
  green. Eval-corpus golden plans keep validating, since the field's type and optionality
  are untouched.
