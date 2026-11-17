## 1. Hygiene test

- [x] 1.1 Create `tests/test_process_hygiene.py` with the pytest-config and `conftest.py` exclusion check
- [x] 1.2 Add the conditional CI-config check: any pytest step must cover all of `tests/` with no file path or `-k`
- [x] 1.3 Add the no-retry checks: dependency list, `--reruns`, `pytest.mark.flaky`, retry-loop pattern
- [x] 1.4 Add the `skip`/`skipif` reason and `xfail(strict=True)` checks via `ast`
- [x] 1.5 Add the `src/*.py` registration check (`FILES.md`, `reference/scripts.md`, referencing test) with a small explicit allowlist
- [x] 1.6 Add a negative test per rule on a tmp tree so each check is shown to fail, not only to pass

## 2. Clear first-run findings

- [x] 2.1 Run `uv run pytest tests/test_process_hygiene.py` and list every violation
- [x] 2.2 Fix each: add missing `FILES.md` / `reference/scripts.md` entries or tests, delete true one-offs, add reasons to bare skips
- [x] 2.3 Add the new test file to `FILES.md`

## 3. Close out

- [x] 3.1 Run the full `uv run pytest tests/` and `ruff check` / `ruff format` on the new file
- [x] 3.2 Move the TODO.md item to `documentation/DONE.md` and update its section in `documentation/todo-pipeline.md`
