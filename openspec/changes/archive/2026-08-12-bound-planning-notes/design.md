## Context

`planning_notes` is a free-string field on `BUILD_PLAN.json`. Two shipped changes already
bound it negatively: `searchable-request-log` banned round-by-round history (that lives
in `request_log`), and `author-owned-placement` banned prose restatement of `placement`.
Neither said what the field is FOR, so the charter at `prompts/planning.md:39` --
"populate `planning_notes` with your reasoning" -- remains the operative instruction and
admits anything.

The field has no declared reader. `prompts/part.md` has no `{{PLANNING_NOTES}}`
substitution; Phase 3's prescribed reads are `parts[]`, `unions`, `interfaces`, and
`request_log_search.py`. One implicit reader exists: on a re-plan the planning agent runs
again against the existing `BUILD_PLAN.json` and therefore opens the field as a side
effect of opening the file, with no instruction on what to do with it.

Two real plans were audited on 2026-08-12 (recorded in `TODO.md` under the rationale-audit
item). HitsterTower yielded five items load-bearing only in `planning_notes`, collapsing
into two categories. C5 Phone-Holder confirmed both and added a third (assembly procedure
plus a required 1.75 mm filament pin that appears in no other field). C5 also showed the
scale of the waste: of 5459 characters, a "Corrections made THIS session" changelog
(already banned), prose restatement of `placement` (already banned), and prose
restatement of `load`, `blocks_needed`, and `intent` (not yet banned) account for roughly
four fifths.

The V1.0 feature freeze (`TODO.md`, 2026-08-12) permits defect correction only. This
change is therefore confined to prompt text, skill-doc text, and one schema *description*
string.

## Goals / Non-Goals

**Goals:**

- Replace the unbounded charter with a positive inclusion rule naming three categories.
- Close the restatement gap generally, not field by field.
- Give the field its one real reader an explicit contract (the re-planner).
- Keep every existing rule number in `prompts/planning.md` stable.

**Non-Goals:**

- No schema structure change: no new property, no type change, no enum, no validator.
  `plan_validate.py` continues not to inspect the field's content.
- No keyhole reader (a `planning_notes_search.py` analogue of `request_log_search.py`).
- No provenance move, no structured `{considered, rejected_because}` entries, no bill of
  materials. All three are post-V1.0 items already filed in `TODO.md`.
- No length limit, character budget, or required section headings.

## Decisions

**D1: Bound by an inclusion rule at the write side, not by a keyhole reader.**
The `TODO.md` item proposed copying the `request_log` solution -- leave the prose alone,
add a reader that never loads it whole. Rejected: the two fields bloat for different
reasons. `request_log` is append-only by construction and cannot shrink, so a reader was
the only option. `planning_notes` is rewritten on every re-plan and already carries a
current-state-only rule, so it does not grow; it bloats because nothing tells the writer
to stop. Bounded to three categories, the field is small enough to load whole (the audit
estimate for HitsterTower is on the order of fifteen lines), and a grep-keyhole would
require inventing mandatory section headings -- a schema change through the back door,
which the freeze excludes anyway.

**D2: Inclusion rule, not an exclusion list.**
Exclusion lists are what the field already has, and they leak: three restatement classes
survived two rounds of bans because each ban named one field. An inclusion rule makes the
default "excluded" and needs no amendment when a new structured field appears.

**D3: Three categories, taken verbatim from the audit, not invented.**
(a) decisions-against, (b) cross-part invariants, (c) assembly procedure and supplied
hardware. Each is grounded in at least two instances across the two audited plans, and
each is load-bearing for a structural reason: `parts[]` is a positive per-part record, so
it cannot express an absence (a), a property of the set (b), or a procedure over the set
(c). An earlier framing -- "`planning_notes` is the plan's negative space" -- covered (a)
and (b) but was falsified by (c); the three-category form is kept rather than forcing a
single slogan.

**D4: Generalize the restatement ban to all structured fields.**
`author-owned-placement` banned `placement` prose specifically and the C5 plan then
restated `load`, `blocks_needed`, and `intent` instead. Naming the general principle --
the structured field is the single source -- costs one rule and closes the class. One
carve-out is stated explicitly: a cross-part *consequence* of a structured value stays
admissible under category (b), otherwise the ban would delete legitimate content (for
example "the feet's X centerlines are fixed by the plate's clevis positions", which is
not a restatement of either part's numbers).

**D5: The re-plan clause goes next to the existing `request_log` carry-forward
instruction (rule 14), not into a new rule.**
Rule numbers 1-15 are cited by number from `skill/phase2_planning.md` and
`skill/phase3_build.md`; `condense-planning-prompt` already had to preserve them. The
re-plan behavior for both fields is one topic and belongs in one place. The contrast is
the substance: `request_log` is carried forward entry by entry and never edited;
`planning_notes` is rewritten and superseded text is deleted.

**D6: Update the schema description string too.**
The current-state-only rule is already stated in the `planning_notes` description in
`src/build_plan_schema.json`. Leaving the inclusion rule out of that description would
split the field's contract across two files with the weaker half at the schema. A
description string is not a constraint, so no plan's validity changes -- the eval-corpus
goldens keep validating unchanged.

## Risks / Trade-offs

**An inclusion rule is unenforced -- nothing validates the field's content.**
→ Accepted deliberately. Enforcement would mean parsing prose or mandating headings,
both of which are schema changes barred by the freeze and rejected in D1. The audit's own
finding is that most of the observed bloat violates rules that were *already* stated but
not followed, so the realistic lever is a clearer, shorter rule at the point of writing.
Category (a) is the natural first candidate for structure if the prose bound does not
hold; that follow-up is already filed in `TODO.md`.

**Category (c) will be partly superseded.**
→ The post-V1.0 bill-of-materials item would take the hardware list out of (c) and leave
it holding only the procedure. Stated in `TODO.md` so the boundary is recorded now
instead of being rediscovered.

**A stricter rule could cause the planner to drop something genuinely load-bearing.**
→ The three categories are derived from a two-project audit, not from first principles,
and category (b)'s carve-out in D4 exists precisely to protect the case most likely to be
misread as restatement. The residual risk is that a third project has a fourth category;
the mitigation is that the field remains free text, so nothing is structurally prevented
from being written.

**Rule renumbering would break cross-references.**
→ D5 keeps numbering stable; the implementation verifies by grepping
`skill/phase2_planning.md` and `skill/phase3_build.md` for rule-number citations after
editing.
