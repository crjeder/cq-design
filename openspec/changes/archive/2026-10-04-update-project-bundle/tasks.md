## 1. skill_version reuse

- [x] 1.1 Confirm `describe_installed()` / `compare()` in `src/skill_version.py` are importable from `bundle_project.py` (same dir); change nothing unless a signature blocks reuse

## 2. bundle_project.py

- [x] 2.1 Write `.bundle_version.json` (`commit`, `dirty`, `bundled_at`) at the end of `bundle()`
- [x] 2.2 Prune files under `lib/blocks`, `lib/exporters` and bundled top-level modules that no longer exist in `src/`; leave other `lib/` files
- [x] 2.3 Write `pyproject.toml` / `.python-version` only if absent; print a note when an existing one differs
- [x] 2.4 Add `--check [DIR]`: read stamp, compare to skill HEAD, print status, exit 0 only for `current`; no writes
- [x] 2.5 In `main()`, after `bundle()`, call `init_permissions.merge_permissions` and `merge_hooks` for DIR

## 3. Tests

- [x] 3.1 `tests/test_bundle_project.py` (no CadQuery): stamp written; prune removes a retired `lib/blocks` file but keeps `lib/my_helper.py`; existing pyproject kept + note; `--check` is `unknown` without a stamp and `current`/`behind` with a fake stamp; permissions merged
- [x] 3.2 Run `tests/test_build_script.py` to confirm `bundle()` still works

## 4. Docs

- [x] 4.1 Add an "Updating an existing project" section to `skill/resume.md` and README: `skill_version.py --compare`, reinstall if stale, `bundle_project.py DIR`, `uv sync`, re-run `build/build.py`
- [x] 4.2 Update the `reference/scripts.md` bundle_project row and the `CLAUDE.md` layout line; fix README "build/" vs "lib/" wording near line 76
