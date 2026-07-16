# Setup: venv, permission bootstrap, printer profile bootstrap

Run once per working directory, immediately after establishing `SKILL_DIR` and before Phase 1.

## Python environment

Python 3.10-3.12 (CadQuery has no wheels for 3.13+), with the venv activated:

```bash
python3.12 -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

```bash
# Windows (cmd / any shell, using Python)
for /f "delims=" %i in ('python -c "import pathlib, sys; print(pathlib.Path(sys.argv[1]).parent.resolve())" "%~f0"') do set SKILL_DIR=%i
```

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
reorders, or duplicates existing entries or other settings keys. The directory
scaffold is likewise idempotent -- it only creates `build/`/`stl/`/`preview/` if
missing and never touches existing contents. On a truly fresh directory the very
first invocation of `init_permissions.py` itself may prompt once; that single
approval seeds everything else.

**Explicit init:** if the user asks to "init permissions" (or to re-seed after updating
the skill), run `python "$SKILL_DIR/src/init_permissions.py" .` unconditionally (skip the
`--check`) so any newly added patterns are merged in.

**Fallback when the helper cannot run:** if `init_permissions.py` is unavailable or its
first run is declined, read `$SKILL_DIR/src/skill_permissions.json` and merge its `allow`
array into `.claude/settings.local.json` yourself with the Read/Write tools (same
additive, dedup, order-preserving merge — do not drop existing entries or other keys),
and create `build/`, `stl/`, `preview/` yourself if they don't already exist.

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
python "$SKILL_DIR/src/printer_profile_validate.py" printer_profile.json
```

```powershell
# Windows (PowerShell)
if (-not (Test-Path printer_profile.json)) {
    Copy-Item "$SKILL_DIR/src/printer_profile.default.json" ./printer_profile.json
    Write-Host "Seeded printer_profile.json with defaults -- edit it to match your printer."
}
python "$SKILL_DIR/src/printer_profile_validate.py" printer_profile.json
```

An existing `printer_profile.json` is never overwritten or re-seeded -- the copy only happens
when the file is absent. When the seed step runs, tell the user in the same turn that a
default profile was created and where to edit it. If validation fails (the file exists but was
hand-edited into an invalid state), report the errors and fall back to asking the user for the
affected field(s) in Phase 1, exactly as if no profile existed.
