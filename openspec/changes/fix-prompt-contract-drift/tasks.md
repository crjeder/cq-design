## 1. Builder section-cut guidance

- [ ] 1.1 Rewrite `prompts/builder.md:41-45`: `--extra-section` cuts replace the bounding-box-center cuts; no `--auto-sections`; for bore/boss cuts run `section_select.py` by hand and pass its `extra_section_args`
- [ ] 1.2 Rewrite the `section_select.py` row in `reference/scripts.md:51`: drop the `render_preview.py --auto-sections` / forwarding sentence, describe it as a standalone CLI whose output feeds `--extra-section`
- [ ] 1.3 Drop `--auto-sections;` from the `section_select.py` line in `FILES.md:65`

## 2. Audit panel labels

- [ ] 2.1 Replace the panel line at `prompts/audit.md:20-21` with "Viewed from South (looking North) top-left, Viewed from West (looking East) top-right, Viewed from above (looking down) bottom-left, isometric bottom-right", keeping the ortho-panel usage sentence

## 3. Planner compression load

- [ ] 3.1 Change `prompts/planning.md:145-146` to `load: {"dir": [0, 0, -1], "type": "compression"}` and note the direction is ignored for scoring

## 4. Verify

- [ ] 4.1 `git grep -n "auto-sections\|looking -Y"` returns no hits outside `openspec/`
- [ ] 4.2 Validate a minimal BUILD_PLAN part with `load: {"dir": [0, 0, -1], "type": "compression"}` through the plan validator (exit 0) and confirm the dir-less form fails
- [ ] 4.3 `uv run pytest tests/test_plan.py` and any prompt-rendering tests pass
- [ ] 4.4 `openspec validate fix-prompt-contract-drift`
