# Setup: venv, permission bootstrap, printer profile bootstrap

Run once per working directory, immediately after establishing `SKILL_DIR` and before Phase 1.

## Python environment

The skill's own uv project supplies Python 3.12 and every dependency; no venv to
activate. Sync it once (idempotent, fast when already synced):

```bash
uv sync --project "$SKILL_DIR"
```

Scripts that import third-party packages are then run as
`uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/<script>.py"`; stdlib-only helpers
(`init_permissions.py`, `request_log_search.py`, `convert_build123d.py`,
`blocks/validate.py`) may use plain `python`.

## Permission bootstrap (first use per directory)

The pipeline issues many `uv run`, `python`, `uv sync`, file-copy, `WebSearch`, and
`WebFetch` commands. To avoid a permission prompt for each one, seed the working
directory's `.claude/settings.local.json` with the patterns these commands need, once
per directory. This same step also scaffolds the working directory's top-level
`build/`, `stl/`, and `preview/` directories up front, so the layout the core SKILL.md
documents exists from the start instead of appearing piecemeal as later phases run.

First check whether this directory was already seeded, then merge if not:

```bash
# --check exits 0 if already seeded, 1 if not
if ! python "$SKILL_DIR/src/init_permissions.py" --check .; then
    python "$SKILL_DIR/src/init_permissions.py" .
fi
```

```powershell
# Windows (PowerShell)
python "$SKILL_DIR/src/init_permissions.py" --check .
if ($LASTEXITCODE -ne 0) { python "$SKILL_DIR/src/init_permissions.py" . }
```

The merge is additive and idempotent: it creates `.claude/settings.local.json` if
absent, appends only missing patterns to `permissions.allow`, and never removes,
reorders, or duplicates existing entries or other settings keys. It also seeds a
`Stop` hook that runs `src/session_cost.py` to record billed token cost into
`build/cost.json` after each turn (a no-op until `build/` exists; added only when no
`session_cost.py` hook is already present) -- the bootstrap output names it alongside
the pattern count. The directory scaffold is likewise idempotent -- it only creates
`build/`/`stl/`/`preview/` if missing and never touches existing contents. On a truly fresh directory the very
first invocation of `init_permissions.py` itself may prompt once; that single
approval seeds everything else.

**Explicit init:** if the user asks to "init permissions" (or to re-seed after updating
the skill), run `python "$SKILL_DIR/src/init_permissions.py" .` unconditionally (skip the
`--check`) so any newly added patterns are merged in.

**Fallback when the helper cannot run:** if `init_permissions.py` is unavailable or its
first run is declined, read `$SKILL_DIR/src/skill_permissions.json` and merge its `allow`
array (and its `hooks` block, with `{session_cost_path}` replaced by the absolute path
to `$SKILL_DIR/src/session_cost.py`) into `.claude/settings.local.json` yourself with
the Read/Write tools (same additive, dedup, order-preserving merge — do not drop
existing entries or other keys), and create `build/`, `stl/`, `preview/` yourself if
they don't already exist.

Known gaps: arbitrary manufacturer `WebFetch` domains and browser MCP tools (whose
server name is environment-dependent) are not in the seeded set and may still prompt.

## Printer profile bootstrap (first use per directory)

`printer_profile.json` in the working directory records a user's default `printer`,
`material`, `nozzle_mm`, and `constraints` so Phase 1 doesn't have to ask for them on every
run. Seed it once per directory, immediately after the permission bootstrap above and before
Phase 1:

```bash
if [ ! -f printer_profile.json ]; then
    cp "$SKILL_DIR/src/printer_profile.default.json" ./printer_profile.json
    echo "Seeded printer_profile.json with defaults -- edit it to match your printer."
fi
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/printer_profile_validate.py" printer_profile.json
```

```powershell
# Windows (PowerShell)
if (-not (Test-Path printer_profile.json)) {
    Copy-Item "$SKILL_DIR/src/printer_profile.default.json" ./printer_profile.json
    Write-Host "Seeded printer_profile.json with defaults -- edit it to match your printer."
}
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/printer_profile_validate.py" printer_profile.json
```

An existing `printer_profile.json` is never overwritten or re-seeded -- the copy only happens
when the file is absent. When the seed step runs, tell the user in the same turn that a
default profile was created and where to edit it. If validation fails (the file exists but was
hand-edited into an invalid state), report the errors and fall back to asking the user for the
affected field(s) in Phase 1, exactly as if no profile existed.

## Model routing config bootstrap (first use per directory)

`skill_config.json` in the working directory names which model runs each LLM role
(`models.planner`, `models.part_author`, `models.fix_loop`). Seed it the same way as
the printer profile, immediately after it:

```bash
if [ ! -f skill_config.json ]; then
    cp "$SKILL_DIR/src/skill_config.default.json" ./skill_config.json
    echo "Seeded skill_config.json with default model routing -- edit it to change which model runs each role."
fi
```

```powershell
# Windows (PowerShell)
if (-not (Test-Path skill_config.json)) {
    Copy-Item "$SKILL_DIR/src/skill_config.default.json" ./skill_config.json
    Write-Host "Seeded skill_config.json with default model routing -- edit it to change which model runs each role."
}
```

An existing `skill_config.json` is never overwritten, re-seeded, or merged. A missing
file is not an error -- Phase 2, Phase 3, and the quality gate's `--fix` path each fall
back to their own documented default (see those sections) when the file or a role key
is absent.
