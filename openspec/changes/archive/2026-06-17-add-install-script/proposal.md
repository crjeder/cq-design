## Why

Installing the cq-design skill today is a manual, undocumented process: a user
must know that Claude Code discovers personal skills under `~/.claude/skills/`,
copy the repository there by hand, and separately run `uv sync` to provision the
Python environment. This is error-prone and a barrier to adoption. A single
installation script makes the skill installable in one command on every
supported platform.

## What Changes

- Add an installation script that copies (or links) the skill into the Claude
  Code personal skills directory (`~/.claude/skills/cq-design/`) so it is
  discoverable by Claude Code.
- The script provisions the Python environment by invoking `uv sync`, and fails
  with a clear message if `uv` is not installed (pointing at the install URL).
- Provide both a POSIX shell entry point (macOS/Linux) and a PowerShell entry
  point (Windows), matching the dual-platform guidance already in `SKILL.md`.
- Support re-running the script idempotently (re-install / update an existing
  install) and an uninstall path to remove the installed skill.
- Document the one-command install in `README.md`.

## Capabilities

### New Capabilities
- `skill-install`: A cross-platform installer that places the cq-design skill in
  the Claude Code skills directory and provisions its Python environment, with
  idempotent re-install and uninstall support.

### Modified Capabilities
<!-- none: no existing spec requirements change -->

## Impact

- New files: installation script(s) at the repository root (e.g.
  `install.sh` and `install.ps1`).
- Modified: `README.md` Setup section to document the installer.
- Dependencies: relies on `uv` (already required) being on PATH; no new runtime
  dependencies.
- No changes to `src/`, the JSON contract, or the pipeline behavior.
