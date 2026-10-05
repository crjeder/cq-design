---
description: Export STL and 3MF for an existing CadQuery script
argument-hint: <script.py>
---

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/run_cadquery_model.py" $ARGUMENTS --deliver --formats stl,3mf
```

The script must assign its geometry to `result`. Report `stl`, `threemf`, and the geometry summary. If `success` is false, show `errors` (each has a `hint`; read it) and stop.
