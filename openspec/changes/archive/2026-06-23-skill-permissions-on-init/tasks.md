## 1. Canonical permission list

- [x] 1.1 Author `src/skill_permissions.json`: the canonical `allow` pattern list (Bash + PowerShell variants) covering `run_cadquery_model.py`/`print_orientation.py`/`model_export.py`/`quality_gate.py`/`plan_validate.py`/`measure_stl.py` runners, the `uv run *`/`uv sync*` fallbacks, the build-bundle `cp`/`Copy-Item` and `mkdir`/`New-Item -ItemType Directory` shapes, `uv run python build/build.py*`, `WebSearch`, and `WebFetch(domain:...)` for the maker sources SKILL.md names.
- [x] 1.2 Cross-check the list against every command shape in SKILL.md (Phases 1-4, `/deliver`, `/render`) so each documented command maps to a pattern; designate the `run_cadquery_model.py` entry as the sentinel.

## 2. Bootstrap helper

- [x] 2.1 Implement `src/init_permissions.py`: resolve `<cwd>/.claude/settings.local.json`, create `.claude/` and the file if absent, load the canonical list from `skill_permissions.json`, merge into `permissions.allow` deduped and order-preserving, write back with 2-space indent, print the added patterns. Leave all other settings keys untouched.
- [x] 2.2 Add a sentinel-detection mode (e.g. `--check`) that exits indicating whether the sentinel pattern is already present, so the skill can decide first-use vs skip without parsing JSON itself.
- [x] 2.3 Type hints + one-line docstrings on public functions; `ruff check`/`ruff format` clean.

## 3. SKILL.md workflow

- [x] 3.1 Add an init/bootstrap step at the start of the pipeline (after `SKILL_DIR` is established, before Phase 1 work): run the sentinel check, and on first use (or explicit init) run `init_permissions.py`; document that a single bootstrap prompt may appear on a fresh directory.
- [x] 3.2 Document an explicit-init entry point (natural-language "init permissions" and/or a note under the slash-command section) that always re-runs the merge.
- [x] 3.3 Note the inline Read/Write fallback for when the helper cannot run.

## 4. Tests

- [x] 4.1 `tests/test_init_permissions.py`: fresh-dir creation, merge into a populated file preserves existing entries and other keys, all-present is a no-op (no duplicates), sentinel `--check` reports present/absent correctly.
- [x] 4.2 Assert the canonical list parses and the sentinel pattern is present in `skill_permissions.json`.

## 5. Docs & verification

- [x] 5.1 README: note that the first run in a directory seeds project-local permissions in `.claude/settings.local.json`.
- [x] 5.2 Run `uv run pytest tests/test_init_permissions.py` and `ruff check`/`ruff format` on changed files.
- [x] 5.3 `openspec validate skill-permissions-on-init`.
