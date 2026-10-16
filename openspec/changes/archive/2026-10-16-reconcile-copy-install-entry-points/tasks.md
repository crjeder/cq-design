## 1. Verify copy and link installs

- [x] 1.1 Copy install into a scratch dir, plugin variables unset: `uv sync`, `init_permissions.py`, profile validation, and a `run_cadquery_model.py` run all pass. Note: a long dest path failed OCP DLL load on Windows ("filename too long"); a short dest passed.
- [x] 1.2 `--link` install passes (links to the repo). A clean-config `claude -p` listed all seven `cq-design:*` commands from a copy install (source `cq-design@skills-dir`); in a live session `/cq-design:status` expanded `${CLAUDE_PLUGIN_ROOT}` to the skills-dir path and `~/.claude/plugins/data/cq-design-skills-dir/` exists.
- [x] 1.3 Findings contradict the original design (commands do load); design.md, proposal.md, and specs revised.

## 2. Document the support matrix

- [x] 2.1 `SKILL.md` Prerequisites: state `SKILL_DIR` = `${CLAUDE_PLUGIN_ROOT}` (plugin or copy install, both define it) or the Base directory path, and that both install modes offer the commands
- [x] 2.2 `README.md` Setup: rename "With the installer (no slash commands)"; state both modes support skill and commands and the venv difference (`<dest>/.venv` vs `${CLAUDE_PLUGIN_DATA}/venv`); note `--link` command loading is unverified
- [x] 2.3 Fix the "Commands:" sentence in the README plugin section if it reads as plugin-only

## 3. Validate

- [x] 3.1 `uv run pytest tests/` and `openspec validate reconcile-copy-install-entry-points`
