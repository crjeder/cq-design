---
description: Design a 3D-printable part as a parametric CadQuery model (full pipeline, phases 0-4)
argument-hint: <what to design>
---

Run the cq-design pipeline, phases 0-4, for: $ARGUMENTS

`SKILL_DIR` is `${CLAUDE_PLUGIN_ROOT}`. Read `${CLAUDE_PLUGIN_ROOT}/SKILL.md` and follow it, including its phase files and the resume rule.

First run `python "${CLAUDE_PLUGIN_ROOT}/src/init_permissions.py" . --check`. If it reports `uninitialized`, do what `/cq-design:init` does (venv in `${CLAUDE_PLUGIN_DATA}/venv`) before Phase 0.
