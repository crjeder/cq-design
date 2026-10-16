## 1. Dedupe init commands

- [x] 1.1 In `SKILL.md` Prerequisites, replace the init bash block with: run `/cq-design:init` logic (see `commands/init.md`)
- [x] 1.2 Check the remaining Prerequisites prose still reads correctly and no other doc repeats the three command lines (grep `init_permissions.py`)
- [x] 1.3 Run `openspec validate skill-init-points-to-command` and `uv run pytest tests/test_plan.py`
