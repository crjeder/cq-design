---
description: Plan a cq-design part (phases 1-2) and stop once BUILD_PLAN.json is approved
argument-hint: <what to design>
---

Run cq-design phases 1-2 only for: $ARGUMENTS

`SKILL_DIR` is `${CLAUDE_PLUGIN_ROOT}`. Read `${CLAUDE_PLUGIN_ROOT}/SKILL.md` and follow its Prerequisites, then `skill/phase0_sourcing.md` (skip it only if the user already chose to build from scratch), `skill/phase1_requirements.md` and `skill/phase2_planning.md`. Stop once `BUILD_PLAN.json` is approved; build no parts.

First run `python "${CLAUDE_PLUGIN_ROOT}/src/init_permissions.py" . --check`. If it reports `uninitialized`, do what `/cq-design:init` does (venv in `${CLAUDE_PLUGIN_DATA}/venv`) first.
