---
description: Prepare this directory for cq-design (uv env, permissions, profile)
---

Set up the current working directory for cq-design. `SKILL_DIR` is `${CLAUDE_PLUGIN_ROOT}`; the venv lives in `${CLAUDE_PLUGIN_DATA}/venv`. Substitute these literal paths in every command. All steps are idempotent.

```bash
UV_PROJECT_ENVIRONMENT="${CLAUDE_PLUGIN_DATA}/venv" uv sync --project "${CLAUDE_PLUGIN_ROOT}"
python "${CLAUDE_PLUGIN_ROOT}/src/init_permissions.py" . --venv "${CLAUDE_PLUGIN_DATA}/venv"
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/printer_profile_validate.py" profile.json
```

The `--venv` flag records `UV_PROJECT_ENVIRONMENT` in `.claude/settings.local.json` so later `uv run --project` calls reuse that venv. Report any file the helper seeded (tell the user to edit it) and any profile validation errors. Do not overwrite existing files.

Then recommend the user start a fresh session before `/cq-design:design`: this session already carries the init output on top of every loaded tool, and each later call re-reads that context.
