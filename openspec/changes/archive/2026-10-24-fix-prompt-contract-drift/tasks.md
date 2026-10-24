## 1. Builder section-cut guidance

Dropped: superseded by `wire-auto-sections`, which made `--auto-sections` real and rewrote the same builder, `reference/scripts.md`, and `FILES.md` paragraphs. The `preview-cross-sections` delta was removed for the same reason.

## 2. Audit panel labels

- [x] 2.1 Replace the panel line at `prompts/audit.md:20-21` with "Viewed from South (looking North) top-left, Viewed from West (looking East) top-right, Viewed from above (looking down) bottom-left, isometric bottom-right", keeping the ortho-panel usage sentence

## 3. Planner compression load

- [x] 3.1 Change `prompts/planning.md:145-146` to `load: {"dir": [0, 0, -1], "type": "compression"}` and note the direction is ignored for scoring

## 4. Verify

Task 4.1 (`git grep "auto-sections"` empty) dropped: superseded by `wire-auto-sections`.

- [x] 4.2 Validate a minimal BUILD_PLAN part with `load: {"dir": [0, 0, -1], "type": "compression"}` through the plan validator (exit 0) and confirm the dir-less form fails
- [x] 4.3 `uv run pytest tests/test_plan.py` and any prompt-rendering tests pass
- [x] 4.4 `openspec validate fix-prompt-contract-drift`
