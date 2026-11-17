---
description: Prepare this directory for cq-design (uv env, permissions, profile)
---

Set up the current working directory for cq-design. `SKILL_DIR` is `${CLAUDE_PLUGIN_ROOT}`; the venv lives in `${CLAUDE_PLUGIN_DATA}/venv`. Substitute these literal paths in every command. All steps are idempotent.

```bash
UV_PROJECT_ENVIRONMENT="${CLAUDE_PLUGIN_DATA}/venv" uv sync --project "${CLAUDE_PLUGIN_ROOT}"
python "${CLAUDE_PLUGIN_ROOT}/src/init_permissions.py" . --venv "${CLAUDE_PLUGIN_DATA}/venv"
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/printer_profile_validate.py" profile.json
```

The `--venv` flag records `UV_PROJECT_ENVIRONMENT` in `.claude/settings.local.json` so later `uv run --project` calls reuse that venv. Report each `.claude/agents/cq-design-*.md` it installed or refreshed (plugin-owned; init overwrites them) and any file the helper seeded (tell the user to edit it) and any profile validation errors. Do not overwrite existing files.

**Orca import** -- only when `init_permissions.py` reported seeding `profile.json` in this run (a pre-existing profile is never imported into; point the user to `/cq-design:sync-profile`):

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/orca_profile.py" discover
```

No installs: keep the default profile and tell the user to edit it. Several: ask which one (its `data_dir` becomes `--data-dir`). Then run `import profile.json [--data-dir D]` and handle its typed error by asking, then re-running with the answer:

- `filament_required`: offer the `choices.user` presets first, then the matching `Generic <material>` from `choices.system` -> `--filament "<name>"` (repeat the flag per loaded filament).
- `unmapped_material`: ask which of the listed materials it behaves like -> `--material X`.
- `machine_required`: ask for the Orca printer preset name -> `--machine "<name>"`.

After a successful import, if `written` has no `max_materials` (one-nozzle machine), ask how many filament slots an AMS/MMU gives (1 without one) and re-run the import with `--max-materials N`.

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/orca_profile.py" import profile.json --filament "<name>" [--max-materials N]
```

Report the imported fields (`written`, old -> new), the `process_reason` line, that the planner may pick another preset per design and the user can always name one, any `skipped` fields with their reason, and each `compensation_warnings` entry: the slicer already compensates that, so model-side compensation would double it. Calibration fields (fit clearances, tolerance, bridge length, wall minimum) are not in Orca; say they keep their defaults.

Then recommend the user start a fresh session before `/cq-design:design`: this session already carries the init output on top of every loaded tool, and each later call re-reads that context.

Finally run `python "${CLAUDE_PLUGIN_ROOT}/src/install_check.py"`; if it reports a duplicate install (plugin and standalone skill both present), show its hint as a warning. Remove nothing and do not fail on it.
