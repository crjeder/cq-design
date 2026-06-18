## 1. Update SKILL.md

- [x] 1.1 In Phase 2 (Planning), add a step after the `plan_validate.py` call that writes the plan JSON to `BUILD_PLAN.json` in the working directory using a Python one-liner or shell redirect.
- [x] 1.2 Add a step that shows the written file path to the user alongside the JSON code block display.
- [x] 1.3 Update the user-edits scenario to reference reading from disk (already the intent, now made explicit).

## 2. Verify spec coverage

- [x] 2.1 Confirm the updated SKILL.md satisfies all three scenarios in `specs/plan-disk-write/spec.md` (first run, overwrite, write failure).
- [x] 2.2 Confirm the updated SKILL.md satisfies the new scenario in `specs/planning-phase/spec.md` (plan written before display).

## 3. Manual smoke test

- [x] 3.1 Run through the planning phase for a simple part (e.g. "a 50x50x20 mm box lid") and verify `BUILD_PLAN.json` appears in the working directory before the approval prompt.
- [x] 3.2 Immediately run `python src/orchestrate.py --plan BUILD_PLAN.json --output-dir build/ --max-retries 1` and verify it reads the file without error.
