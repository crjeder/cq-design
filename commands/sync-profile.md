---
description: Refresh profile.json from the OrcaSlicer-family presets (machine, process, filament)
argument-hint: "[--machine M] [--process P] [--filament F ...] [--max-materials N]"
---

Re-import the Orca-sourced fields of `./profile.json`. `$ARGUMENTS` pass through; without them the presets recorded in `profile.json`'s `orca` block are re-read. Calibration fields (fit clearances, tolerance, bridge length, wall minimum, output format) are never changed.

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/orca_profile.py" import profile.json $ARGUMENTS
```

With no `orca` block yet, handle the typed errors as `/cq-design:init` does (`ambiguous_data_dir` -> ask and pass `--data-dir`, `filament_required` -> ask from `choices`, `unmapped_material` -> ask and pass `--material`), and ask for the AMS/MMU slot count when the machine has one nozzle.

Report every `written` field as `old -> new` (or "already up to date" when empty), the `process_reason`, any `skipped` fields with their reason, and each `compensation_warnings` entry.
