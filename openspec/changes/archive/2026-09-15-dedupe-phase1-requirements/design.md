## Context

Editorial-only change to one doc file (`skill/phase1_requirements.md`). None
of the design.md trigger conditions apply (not cross-cutting, no new
dependency, no security/perf/migration concern, no technical ambiguity) —
included only because the schema requires it before `tasks`.

## Goals / Non-Goals

**Goals:**
- Remove the three identified duplications without losing any rule.

**Non-Goals:**
- Restructuring the file further, or touching other phase files.

## Decisions

- Keep each rule's *first* occurrence (its original, fuller context) and cut
  the later restatement, replacing it with a short cross-reference where the
  later spot needs to recall the rule applies there too.
- For the topology aside (lines 58-60), cut the sentence entirely rather than
  cross-reference, since the exit checkpoint section already opens by calling
  itself "the single gate out of Phase 1" — the aside adds no fact the reader
  doesn't already have by the time they reach the exit checkpoint heading.

## Risks / Trade-offs

- [Cutting a restatement could weaken a rule a reader only skims the exit
  checkpoint section for] → Mitigation: replace with a one-clause pointer
  back to "Ask vs. assume" / the topology section rather than deleting outright,
  so the rule is still visible at the point of use.
