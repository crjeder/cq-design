## 1. Edit phase1_requirements.md

- [x] 1.1 In the exit checkpoint's Approval section, replace the restated
      "no `-1` may leave Phase 1" sentence with a short pointer back to "Ask
      vs. assume", keeping the concrete "resolve to a sourced value or convert
      to `assumed`" instruction in place.
- [x] 1.2 In the Phase 1 exit checkpoint intro, collapse "takes one approval
      covering both" and the following "Do not present ... as two separate
      approval rounds" sentence into a single sentence.
- [x] 1.3 In the topology section, cut the two-line aside re-explaining its
      relationship to the exit checkpoint (currently the lines noting this
      confirm "stays a separate, earlier round" and that the exit checkpoint
      "does not re-ask topology"), keeping only the fact that topology
      confirmation happens before dimension lookups/the plan.

## 2. Verify

- [x] 2.1 Re-read the edited file top to bottom and confirm each of the three
      rules (`-1` ban, one-approval, topology-vs-checkpoint) appears exactly
      once, with no rule's substance lost.
- [x] 2.2 Confirm no other file references the removed sentences by exact
      wording (grep for the cut phrasing across `skill/` and `SKILL.md`).
