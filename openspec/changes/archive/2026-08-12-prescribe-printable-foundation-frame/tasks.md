## 1. Prompt update

- [x] 1.1 In `prompts/part.md`'s "Coordinate vocabulary" section, extend the existing
      Z=0-bottom recommendation with one to two sentences naming the floating-
      assembled-frame case and the paired `placement.translate_mm` write-back (contract
      rule 6), per the `part-authoring-guidance` delta spec's "Floating assembled frame
      names the paired pattern" scenario.
- [x] 1.2 Confirm the wording stays a recommendation, not a new modal rule (no
      MUST/SHALL), consistent with `part-authoring-guidance`'s existing "authoring frame
      is the author's choice" requirement.

## 2. Verification

- [x] 2.1 Re-read the edited section end to end to confirm the Z=0 recommendation and
      the floating-frame addition read as one continuous piece of guidance, not two
      competing rules.
- [x] 2.2 Run `uv run pytest tests/test_plan_validate.py tests/test_eval_corpus.py` to
      confirm the prompt edit didn't disturb anything schema/corpus-related (expected:
      no change, since this is prose-only).
