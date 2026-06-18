## 1. Complexity gate

- [x] 1.1 In SKILL.md Phase 3, document the per-part complexity gate: build progressively when the part has >= 1 `interfaces` entry OR `blocks_needed` count >= threshold; otherwise autonomous
- [x] 1.2 State the threshold as a tunable value (default `3` blocks) inline so it can be adjusted from field experience
- [x] 1.3 Document the user override: how the user forces progressive or autonomous regardless of the gate, and that no override means the gate decides

## 2. Staged build flow

- [x] 2.1 Document the stage sequence in SKILL.md: base shape -> features -> finishing, each writing the current `build/<part_id>.py`
- [x] 2.2 Specify that each stage is run through `run_cadquery_model.py --preview` and geometry errors are fixed before its checkpoint is shown
- [x] 2.3 Specify that the visual self-review checklist runs per stage, scoped to the features expected so far
- [x] 2.4 Specify the completion bar: the final stage must satisfy plan dimensions and pass the full visual self-review, same as the autonomous path

## 3. Checkpoint interaction

- [x] 3.1 Document the checkpoint: display the staged preview PNG plus a one-line summary of what the stage added, then wait for the user
- [x] 3.2 Document the three responses: approve (advance / complete), request change (re-author current stage, re-validate, re-present), skip remaining (finish autonomously, no further checkpoints)

## 4. SKILL.md integration and consistency

- [x] 4.1 Place the progressive-build documentation in Phase 3 so it composes with Step 4 (geometry-first, then visual self-review) rather than duplicating it
- [x] 4.2 Ensure the autonomous loop remains the documented default for simple parts and is unchanged in behavior
- [x] 4.3 Re-read Phase 3 end-to-end to confirm mode selection, staging, checkpoints, and the existing 3-attempt autonomous fallback are mutually consistent

## 5. Verification

- [x] 5.1 Confirm no `src/` or wrapper JSON contract changes were introduced (rendering and error types unchanged)
- [x] 5.2 Run `openspec validate progressive-build-checkpoints` and resolve any reported issues
