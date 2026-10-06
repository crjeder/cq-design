---
description: Generate model files (3mf, stl, step, ...) with the project build script
argument-hint: [format[,format...]]
---

Only in a directory that has `build/build.py`; otherwise stop and suggest `/cq-design:init` or `/cq-design:update`. With a format argument (`3mf`, `stl`, `step`, `obj`, `iges`, `scad`; comma-separated for several):

```bash
uv run python build/build.py --formats $ARGUMENTS
```

With no argument, omit `--formats` so `build.py` writes the profile's preferred format:

```bash
uv run python build/build.py
```

Files land in `out/`. Report the files `build.py` printed. On a non-zero exit show the `build failed:` message and stop.
