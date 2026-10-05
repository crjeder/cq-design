---
description: Render a multi-view preview PNG for an existing CadQuery script
argument-hint: <script.py>
---

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/run_cadquery_model.py" $ARGUMENTS --preview
```

The script must assign its geometry to `result`. Show `preview`. If `success` is false, show `errors` (each has a `hint`; read it) and stop.
