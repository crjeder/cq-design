## Context

The repo root is the skill root: `SKILL.md`, `src/`, `skill/`, `prompts/`, `reference/`, `templates/`, `pyproject.toml`, `uv.lock`. Scripts are invoked as `uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/<x>.py"`; `uv sync --project` creates `.venv` inside `SKILL_DIR`. A plugin install is a cache copy whose root changes on every update, and `${CLAUDE_PLUGIN_ROOT}` is substituted in command/skill Markdown bodies but is not exported to Bash-tool commands.

## Goals / Non-Goals

**Goals:**
- Install and update through `/plugin`, with no file moves in the repo.
- Every command works from a project directory without the user knowing the install path.
- The venv survives plugin updates.

**Non-Goals:**
- Removing the installer scripts.
- Changing pipeline phases, scripts' CLIs, or the JSON contract.
- Plugin-level hooks (`init_permissions.py` already writes project-local hooks).

## Decisions

1. **Repo root = plugin root, skill via `"skills": ["."]`.** Alternative: move `SKILL.md` to `skills/cq-design/`, which breaks every `$SKILL_DIR/src` and `skill/` relative path and the installers. Root-as-skill moves nothing. Verify with `claude plugin validate`.
2. **Commands as `commands/<name>.md`, invoked `/cq-design:<name>`.** The plugin name supplies the prefix, so files are named `design.md`, not `cq-design-design.md`. The docs prefer `skills/` over `commands/` for new plugins, but a skill per command would need seven directories for one-screen bodies; revisit if `commands/` is dropped.
3. **`SKILL_DIR` = `${CLAUDE_PLUGIN_ROOT}`, written literally in each command body** (substituted on load), then used in the same `uv run --project` lines as today. It is not a shell variable, so bodies state the literal path, as `SKILL.md` already instructs. On Windows it arrives with forward slashes.
4. **Venv in `${CLAUDE_PLUGIN_DATA}/venv` via `UV_PROJECT_ENVIRONMENT`.** `uv sync` into the plugin root would be wiped on update. Commands prefix scripts with the env var. Alternative: a `bin/` wrapper that sets it; cleaner, but a `bin/` directory blocks claude.ai/Cowork install. Start inline; add a wrapper only if it gets repetitive.
5. **Command set.** `design` (phases 0-4), `plan` (phases 1-2), `init` (the SKILL.md Prerequisites block: `uv sync`, `init_permissions.py`, profile validation), `update` (`bundle_project.py`, contract unchanged), `deliver`, `render`, `status` (`skill_version.py`, `bundle_project.py --check`, profile validation; read-only). `design` and `plan` run the init steps first when `init_permissions.py --check` fails, so `init` is optional for new users.
6. **Marketplace in the same repo** (`marketplace.json`, plugin `source: "./"`). Install: `/plugin marketplace add <owner>/<repo>`, then `/plugin install cq-design@<marketplace>`. `plugin.json` sets `version` so updates are explicit.

## Risks / Trade-offs

- [Everything at the root (`tests/`, `evals/`, `openspec/`) is cached with the plugin] -> acceptable; trim later if size matters.
- [`UV_PROJECT_ENVIRONMENT` not behaving as assumed] -> task 1.3 verifies with a real `uv sync` before commands are written around it.
- [`${CLAUDE_PLUGIN_ROOT}` not substituted when the skill loads by description trigger] -> keep the "Base directory for this skill" line as the fallback in `SKILL.md`.
- [Skill installed both ways gives two copies] -> README states they are alternatives; `status` reports which one is running.
- [`init_permissions.py` hooks embed absolute script paths into the plugin cache and go stale on update] -> `update` re-merges hooks; task 3.2 verifies.

## Migration Plan

Additive. Installer users keep working. To move to the plugin: `install.sh --uninstall`, add the marketplace, install, run `/cq-design:update` in each bundled project. Rollback: remove the plugin, re-run the installer.

## Open Questions

- Bare `/cq-design` shortcut: the root skill is likely addressed as `/cq-design:cq-design`; `/cq-design:design` is the documented entry. Confirm when validated.
- Whether `/plugin update` picks up commits without a `version` bump (pinned when `version` is set).
