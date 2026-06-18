## 1. Visual review checklist reference

- [x] 1.1 Create `reference/Visual Review Checklist.md` with the checklist items: overall shape matches the request, all planned features/interfaces present, proportions reasonable, no floating/disconnected bodies, flat bed face at Z = 0, orientation matches the plan
- [x] 1.2 Phrase each item as a concrete pass/fail check (named item, not open-ended judgment) so a single failed item is an unambiguous mismatch

## 2. SKILL.md part loop integration

- [x] 2.1 In Phase 3 "Setup", add `reference/Visual Review Checklist.md` to the list of files read into context before the loop
- [x] 2.2 In Phase 3 Step 4 "Decide", add the visual self-review: after geometry passes, evaluate the preview PNG against the checklist before marking the part done
- [x] 2.3 Update the done-condition so a part is done only when geometry validation passes AND the visual review confirms intent
- [x] 2.4 Wire `visual_mismatch` into the retry path: on mismatch within the attempt budget, record the discrepancy and retry with a targeted fix driven by that description
- [x] 2.5 Ensure geometry errors are handled first and the visual review is skipped for an attempt whose geometry validation failed
- [x] 2.6 Confirm the exhausted-budget fallback covers an unresolved `visual_mismatch` (summarize, ask user to hint / accept as-is / skip)

## 3. Error-handling reference

- [x] 3.1 Add a `visual_mismatch` row to the SKILL "Error handling reference" table with meaning and corrective action
- [x] 3.2 Note in the table or surrounding text that `visual_mismatch` is recorded by Claude in the loop and is NOT emitted by `run_cadquery_model.py`

## 4. Verification

- [x] 4.1 Re-read SKILL.md Phase 3 end-to-end to confirm the loop logic is consistent (priority order, done-condition, retry budget, fallback)
- [x] 4.2 Confirm no `src/` or wrapper JSON contract changes were introduced (rendering and error types unchanged)
- [x] 4.3 Run `openspec validate visual-self-review` and resolve any reported issues
