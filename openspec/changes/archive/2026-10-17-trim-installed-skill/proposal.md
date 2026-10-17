## Why

The installed copy of the skill points an agent at things it does not ship and ships things no agent needs. Phase docs cite OpenSpec capability names (`planning-phase`, `fem-wall-shell-solve`, `fem-stress-advisor`, `quality-gate-fix-policy`, `toolpath-speed-advisor`) while `openspec/` is never installed; `SKILL.md` and `skill/resume.md` name `install.sh` / `install.ps1`, which the PowerShell installer excludes; `reference/scripts.md` describes `evals/` and `tests/`. Meanwhile the install carries about 2.3 MB of dev baggage (`TODO.md`, `documentation/`, `src/*.egg-info/`, `src/.fossil/`), because both installers copy by exclusion list and the two lists have already drifted apart. Two runtime reads also sit in dev-only directories: `session_cost.py` prices against `evals/model_prices.json` and `render_prompt.py sourcing` reads `documentation/Block_Sources.md`, so a PowerShell copy install silently loses its cost record today.

## What Changes

- Replace each OpenSpec capability-name citation in shipped prose (`skill/phase3_build.md`, `skill/phase4_deliver.md`, `reference/FDM 3D Print Design Guidelines.md`) with a pointer to a shipped file (`reference/scripts.md`, `reference/Engineering Design Rules.md`, a `skill/` section) or drop the parenthetical.
- `SKILL.md` and `skill/resume.md` say "reinstall from the repo" / "an installer copy" without naming `install.sh` / `install.ps1`.
- `reference/scripts.md` drops its `evals/run_evals.py` row and its `tests/` mentions; the eval-runner contract moves to `evals/README.md`.
- Move `evals/model_prices.json` to `src/model_prices.json` (read by `session_cost.py` at runtime and by `evals/run_evals.py`).
- Move `documentation/Block_Sources.md` to `reference/Block_Sources.md` (read by `render_prompt.py sourcing` at runtime).
- **BREAKING (installer contents)**: `install.sh` and `install.ps1` copy by a shared allowlist instead of an exclusion list: `SKILL.md`, `.claude-plugin/`, `commands/`, `skill/`, `prompts/`, `reference/`, `src/`, `templates/`, `pyproject.toml`, `uv.lock`, `.python-version`, `LICENSE`. Inside `src/`, `*.egg-info/`, `.fossil/` and `__pycache__/` are pruned. `TODO.md`, `documentation/`, `CLAUDE.md`, `FILES.md`, `README.md`, `tests/`, `evals/`, `openspec/` and the installers themselves are no longer installed.
- `FILES.md` becomes the single repo layout tree (CLAUDE.md's current `File Layout` tree replaces its stale content); `CLAUDE.md` links to it instead of carrying its own tree.
- `tests/test_prose_layer.py` gains a check that shipped prose (`SKILL.md`, `commands/`, `skill/`, `prompts/`, `reference/`) names no repo-only path or OpenSpec capability name, and a check that both installers carry the same allowlist.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-install`: the installer copies an explicit allowlist (shared by both entry points) instead of excluding throwaway artifacts.
- `plugin-packaging`: the installer is no longer required to stay "unchanged"; `SKILL.md` refers to an installer copy without naming the scripts.
- `prose-layer-validation`: new requirement that shipped prose references nothing outside the install (OpenSpec capability names, `install.*`, `tests/`, `evals/`, `documentation/`, `openspec/`, `TODO.md`).
- `session-token-cost`: price table path moves from `evals/model_prices.json` to `src/model_prices.json`.
- `eval-harness`: same price-table path change.
- `sourcing-prompt-rendering`: corpus source moves from `documentation/Block_Sources.md` to `reference/Block_Sources.md`.
- `claude-md-script-index`: the one-line-per-script index lives in `FILES.md`, which `CLAUDE.md` points to; `evals/` script contracts live in `evals/README.md`, not the shipped `reference/scripts.md`.

## Impact

- Files: `install.sh`, `install.ps1`, `SKILL.md`, `skill/phase3_build.md`, `skill/phase4_deliver.md`, `skill/resume.md`, `reference/scripts.md`, `reference/FDM 3D Print Design Guidelines.md`, `src/session_cost.py`, `src/render_prompt.py`, `src/skill_version.py` (docstring), `evals/run_evals.py`, `evals/README.md` (new), `CLAUDE.md`, `FILES.md`, `README.md` (Block_Sources link), `tests/test_prose_layer.py`, plus tests touching the moved files.
- Existing copy installs keep stale files until reinstalled; the installer already wipes the destination before copying, so a reinstall cleans them.
- Plugin installs (marketplace, `skills: ["."]`) still receive the whole repo; this change does not alter that path.
