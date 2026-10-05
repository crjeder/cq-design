---
description: Report installed cq-design version, project bundle staleness, and profile validity (read-only)
---

Run all three, change nothing, and summarize in a few lines:

```bash
python "${CLAUDE_PLUGIN_ROOT}/src/skill_version.py"
python "${CLAUDE_PLUGIN_ROOT}/src/bundle_project.py" --check .
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/printer_profile_validate.py" profile.json
```

If the bundle is `behind`, suggest `/cq-design:update`. If `profile.json` is missing or invalid, suggest `/cq-design:init` or list the errors. A non-zero exit from a step is a result to report, not a failure to retry.
