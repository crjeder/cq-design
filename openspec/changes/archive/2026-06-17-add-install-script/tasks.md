## 1. POSIX installer (install.sh)

- [x] 1.1 Add `install.sh` at the repo root with a shebang and `set -euo pipefail`
- [x] 1.2 Resolve the repo root from the script path and the destination from `--dest`/`CLAUDE_SKILLS_DIR`, defaulting to `~/.claude/skills/cq-design`
- [x] 1.3 Preflight: verify `uv` is on PATH; if missing, print the install URL (https://docs.astral.sh/uv/) and exit non-zero before touching the skills directory
- [x] 1.4 Copy mode: stage skill files into the destination excluding `.git`, `.venv`, `__pycache__`, `.*_cache`, `build/`, `BUILD_PLAN.json` (rsync with excludes, or tar/cp fallback)
- [x] 1.5 `--link` mode: create a symlink from the destination to the repo instead of copying; report a clear error on failure
- [x] 1.6 Run `uv sync` with the destination as the project dir; exit zero only on success
- [x] 1.7 `--uninstall`: remove only `~/.claude/skills/cq-design` and report
- [x] 1.8 Print the destination path and a success message; support `-h/--help`

## 2. PowerShell installer (install.ps1)

- [x] 2.1 Add `install.ps1` at the repo root mirroring install.sh behavior (params: `-Dest`, `-Link`, `-Uninstall`, `-Help`)
- [x] 2.2 Resolve repo root and destination (`-Dest`/`$env:CLAUDE_SKILLS_DIR`, default `$HOME\.claude\skills\cq-design`)
- [x] 2.3 Preflight `uv` via `Get-Command uv`; on miss, print install URL and exit non-zero before mutating anything
- [x] 2.4 Copy mode with the same exclusion list; `-Link` via `New-Item -ItemType SymbolicLink` with a clear error if denied
- [x] 2.5 Run `uv sync` in the destination; propagate failure as non-zero exit
- [x] 2.6 `-Uninstall` removes only the cq-design destination

## 3. Documentation

- [x] 3.1 Update `README.md` Setup section to document the one-command install for both platforms, the `--link`/`-Link` and uninstall options, and the `uv` prerequisite

## 4. Verification

- [x] 4.1 Run `install.sh`/`install.ps1` into a temp `CLAUDE_SKILLS_DIR` and confirm the destination contains `SKILL.md`, `src/`, `prompts/`, `reference/` and a working `.venv`, with excluded artifacts absent
- [x] 4.2 Confirm the uv-missing path exits non-zero and writes nothing (simulate by overriding PATH)
- [x] 4.3 Re-run the installer over the existing temp install and confirm it refreshes idempotently
- [x] 4.4 Run the uninstall path and confirm only the cq-design directory is removed
