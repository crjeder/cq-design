## 1. Update Step 3 authoring guidance

- [x] 1.1 In `skill/phase3_build.md`, replace the conditional `--extra-section`
      guidance (the "if this part unions a feature into a body that already has a
      cavity..." paragraph, ~lines 335-345) with an unconditional rule: every
      named+positioned `interfaces[]` entry selected by the ranking in 1.2 gets a
      `--extra-section axis=value_mm` cut.
- [x] 1.2 Add the selection procedure: build the candidate list from the same
      named+positioned `interfaces[]` entries already used for `--callout`; for each
      candidate name run `request_log_search.py BUILD_PLAN.json --query "<name>"` and
      record the highest-priority `kind` match found (`clarification` > `correction` >
      none); sort into 3 tiers per design.md D2; cap the combined selection at 3
      (design.md D3).
- [x] 1.3 Add the axis-choice rule per candidate: normal to `wall` when the interface
      declares one, else the axis of `position_mm`'s largest-magnitude component
      relative to the part bbox center (design.md D4).
- [x] 1.4 State explicitly that the bbox-centerline fallback (3 center cuts) only
      applies when a part has zero named+positioned interfaces.

## 2. Verify against existing test/eval coverage

- [x] 2.1 Re-read `tests/test_eval_corpus.py` and any preview-related eval cases to
      confirm nothing asserts on the old conditional wording or the old default
      fallback-heavy behavior; this change is doc/procedure-only so no test code
      should need edits, but confirm no case golden output assumed bbox-center cuts
      for a part that has named interfaces.
- [x] 2.2 Spot-check `skill/phase3_build.md` renders correctly (no broken cross-refs)
      after the edit -- grep for the two other places in the file that reference
      `--extra-section`/`--callout` construction to keep the wording consistent.

## 3. Close out

- [x] 3.1 Update `TODO.md` line 17's item: mark it done, summarizing the shipped rule
      (unconditional selection, 3-tier request_log ranking, cap of 3, wall-normal axis
      default) and note the two explicitly deferred open questions from design.md
      (variable cap, tier-3 starvation) as follow-ups if not resolved.
