## 1. Script

- [x] 1.1 Add `src/install_check.py` (stdlib only): resolve config/skills dirs from env or `--config-dir` / `--skills-dir`, find plugin via `installed_plugins.json`, find standalone via `SKILL.md`, read commit from `.version.json` or symlink target git HEAD, print JSON (and one text line without `--json`)
- [x] 1.2 Add `tests/test_install_check.py` with `tmp_path` fixtures: both, plugin only, standalone only, differing commits, missing/corrupt registry, stale `installPath`

## 2. Commands and docs

- [x] 2.1 Add the `install_check.py` step to `commands/status.md` and report a duplicate with both paths
- [x] 2.2 Add the `install_check.py` step to `commands/init.md` as a warning only
- [x] 2.3 Add the script to `FILES.md` and a contract entry to `reference/scripts.md`

## 3. Close out

- [x] 3.1 Run `uv run pytest tests/test_install_check.py tests/test_skill_version.py` and `ruff check` / `ruff format` on the new files
- [x] 3.2 Remove the TODO.md line 25 item and its `documentation/todo-pipeline.md` entry; add to `documentation/DONE.md`
