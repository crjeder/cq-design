## Why

`src/skill_permissions.json` says its seed is "read/scaffold/build shapes only -- no
destructive verbs", but it grants `Bash(cp *)`, `Bash(mkdir *)`, `PowerShell(Copy-Item *)`
and `PowerShell(New-Item -ItemType Directory *)` (overwrite any file the user can write),
bare `WebSearch` (unrestricted), and `python * <script>.py *` / `uv run --project * python *
<script>.py *` shapes that match any script of that name anywhere on disk (e.g. a
`log.py` in an untrusted checkout). The seed is written without a prompt by
`init_permissions.py`, so every over-broad entry is a silent standing grant.

## What Changes

- Remove `Bash(cp *)`, `Bash(mkdir *)`, `PowerShell(Copy-Item *)`,
  `PowerShell(New-Item -ItemType Directory *)`. No skill-issued command uses them: file
  copies run inside `bundle_project.py` / `init_permissions.py` (Python), and
  `init_permissions.py` already creates `build/`, `stl/`, `preview/`.
- Remove bare `WebSearch`; the per-domain `WebFetch(domain:...)` entries stay.
- Anchor every `python` / `uv run --project` script pattern to the skill directory: the
  canonical list carries a `{skill_dir}` placeholder that `init_permissions.py` resolves
  to the absolute skill root at seed time (same mechanism as the hooks' `{log_path}`).
  The sentinel becomes the resolved `run_cadquery_model.py` pattern.
- The merge drops the skill's own retired broad patterns and stale anchored patterns from
  a previous skill path (plugin update), and reports what it removed. User-authored
  entries are never touched. **BREAKING** for anyone relying on the seeded `cp`/`mkdir`/
  `WebSearch` grants: those calls now prompt.
- Rewrite the `_comment` so it states what the seed actually allows.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `skill-permission-bootstrap`: canonical set drops copy/mkdir/WebSearch shapes and
  anchors script patterns to the skill path; the merge may remove the skill's own retired
  or stale patterns (previously it never removed anything); first-use detection uses the
  resolved sentinel.

## Impact

- `src/skill_permissions.json`, `src/init_permissions.py` (placeholder resolution,
  retired/stale pruning, resolved sentinel), `tests/test_init_permissions.py`.
- `bundle_project.py` inherits the change through `merge_permissions` (no edit expected).
- Docs: `SKILL.md` manual-merge fallback (must substitute `{skill_dir}`),
  `reference/scripts.md` `init_permissions.py` entry.
- Existing working directories: `--check` reports `uninitialized` until re-init, which
  then prunes the old broad entries.
