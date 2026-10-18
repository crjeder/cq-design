## 1. Canonical list

- [x] 1.1 Check the Claude Code permission-rule docs for how Bash/PowerShell rules match quoted paths; pick the template quoting accordingly
- [x] 1.2 In `src/skill_permissions.json`, rewrite every `python * <script>.py *` and `uv run --project * python * <script>.py *` entry (Bash and PowerShell) to the `{skill_dir}`-anchored form (`blocks/validate.py` -> `{skill_dir}/src/blocks/validate.py`), and update `sentinel` to match
- [x] 1.3 Remove `Bash(cp *)`, `Bash(mkdir *)`, `PowerShell(Copy-Item *)`, `PowerShell(New-Item -ItemType Directory *)`, and `WebSearch`
- [x] 1.4 Add a `retired` list holding every removed and pre-anchoring string verbatim
- [x] 1.5 Rewrite `_comment` to describe exactly what the set allows (skill-anchored script runs, `uv sync`, `build/build.py`, named-domain WebFetch)

## 2. init_permissions.py

- [x] 2.1 Resolve `{skill_dir}` (absolute parent of `src/`) in `allow` and `sentinel`, reusing the `_resolve_command` placeholder approach
- [x] 2.2 `is_initialized` / `--check` compare against the resolved sentinel
- [x] 2.3 `merge_permissions` drops `retired` entries and anchored entries resolved against another skill dir, preserving order of the rest; return/print removed entries alongside added ones (update `main()` and `bundle_project.py` call site only if the return shape changes)

## 3. Tests

- [x] 3.1 Update `tests/test_init_permissions.py` for resolved patterns (fresh-dir equality, sentinel check, existing `WebSearch` preservation test now expects pruning)
- [x] 3.2 Add: retired entries pruned and reported, user entries kept in order
- [x] 3.3 Add: stale-path anchored entry replaced by the current-path one; second merge is a no-op
- [x] 3.4 Add: no allow entry contains `cp `, `mkdir`, `Copy-Item`, `New-Item`, or equals `WebSearch`; every script entry contains the resolved skill dir
- [x] 3.5 Run `uv run pytest tests/test_init_permissions.py tests/test_bundle_project.py` (or the bundle test file that exists)

## 4. Docs

- [x] 4.1 `SKILL.md` manual-merge fallback: say to substitute `{skill_dir}` with `SKILL_DIR`
- [x] 4.2 `reference/scripts.md` `init_permissions.py` entry: placeholder resolution, retired/stale pruning
- [ ] 4.3 Manually confirm on Windows that a documented `uv run --project ... log.py journal append ...` call matches without a prompt
