---
description: Re-copy the plugin's tooling into this project's lib/ and build/build.py
---

Only in a directory that already has `lib/` or `.bundle_version.json`; otherwise stop and say the project was never bundled (run `/cq-design:design` instead). Then:

```bash
python "${CLAUDE_PLUGIN_ROOT}/src/bundle_project.py" .
```

This always copies: `build_template.py` to `build/build.py`, the bundled modules and `blocks`/`exporters` to `lib/`, prunes retired files, merges permissions, and restamps `.bundle_version.json`. Report the new stamp commit and suggest `uv sync` and `uv run python build/build.py`; do not run them or edit part scripts.
