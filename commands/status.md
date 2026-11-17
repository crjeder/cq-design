---
description: Report installed cq-design version, project bundle staleness, and profile validity and Orca snapshot state (read-only)
---

Run all four, change nothing, and summarize in a few lines:

```bash
python "${CLAUDE_PLUGIN_ROOT}/src/skill_version.py"
python "${CLAUDE_PLUGIN_ROOT}/src/bundle_project.py" --check .
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/printer_profile_validate.py" profile.json
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/orca_profile.py" check profile.json
```

If the bundle is `behind`, suggest `/cq-design:update`. If `profile.json` is missing or invalid, suggest `/cq-design:init` or list the errors. Orca snapshot: `stale` -> list the `changed` fields and suggest `/cq-design:sync-profile`; `unavailable` -> say the snapshot is used as is; `not_imported` -> mention `/cq-design:sync-profile` imports from Orca. A non-zero exit from a step is a result to report, not a failure to retry.

Also run `python "${CLAUDE_PLUGIN_ROOT}/src/install_check.py"` and, if it reports a duplicate install, show both paths and the removal hint (and say so when the copies are at different commits).
