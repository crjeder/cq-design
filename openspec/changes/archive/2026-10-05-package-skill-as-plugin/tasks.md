## 1. Manifest and environment

- [x] 1.1 Add `.claude-plugin/plugin.json` (name, version, description, author, license, `"skills": ["."]`)
- [x] 1.2 Add `.claude-plugin/marketplace.json` with the plugin sourced at `./`
- [x] 1.3 Verify `UV_PROJECT_ENVIRONMENT=<dir>` makes `uv sync --project` build the venv outside the project; fix the design if not
- [x] 1.4 Run `claude plugin validate .` (passes; skill-naming question stays open until task 4.2)

## 2. Commands

- [x] 2.1 `commands/init.md`: Prerequisites block (uv sync with data-dir venv, `init_permissions.py`, profile validation)
- [x] 2.2 `commands/design.md` and `commands/plan.md`: init-if-needed, then phases per `SKILL.md`
- [x] 2.3 `commands/update.md`: move the `/cq-design:update` section from `SKILL.md`
- [x] 2.4 `commands/deliver.md` and `commands/render.md`: move the `/deliver` `/render` section
- [x] 2.5 `commands/status.md`: version, bundle `--check`, profile validate; read-only

## 3. Skill and docs

- [x] 3.1 Trim `SKILL.md`: remove the command table and moved sections, keep the `${CLAUDE_PLUGIN_ROOT}` / base-directory fallback for `SKILL_DIR`
- [x] 3.2 Confirm `bundle_project.py` refreshes the hook paths written by `init_permissions.py` after a plugin update; fix if stale
- [x] 3.3 README install section (plugin first, installer as alternative); CLAUDE.md file layout entry for `.claude-plugin/` and `commands/`
- [x] 3.4 Delta for `skill-doc-structure` (command entry points moved to `commands/`); no tests enumerate SKILL.md content

## 4. Verification

- [x] 4.1 `uv run pytest tests/test_plan.py tests/test_skill_version.py` plus any doc-structure tests
- [ ] 4.2 Install via local marketplace (`/plugin marketplace add .`), run `status`, `init`, `render` on a fixture script from a clean directory
- [ ] 4.3 Simulate an update (bump version) and confirm the venv in `${CLAUDE_PLUGIN_DATA}` is reused
