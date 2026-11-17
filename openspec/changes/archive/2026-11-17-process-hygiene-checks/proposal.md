## Why

The text-to-cad survey (2026-10-16) found a short process-hygiene list in that project's
`AGENTS.md`: every test file reached by CI, flaky tests fixed or deleted and never
retried, no one-off helper scripts in `src/`. None of it is enforced here. The repo has
no CI workflow at all, 90 test files rely on `testpaths` alone, and `src/` has grown
by one-line additions to `FILES.md` that nothing cross-checks. A rule nobody checks drifts.

## What Changes

- Add `tests/test_process_hygiene.py`, a pytest module that fails when a hygiene rule is broken. No new `src/` script: the check is repo hygiene, not a pipeline tool, and a helper script for it would break its own rule.
- Rule 1, tests are reached: pytest config has no `--ignore`, `--deselect` or `collect_ignore`; every `tests/test_*.py` is collectable; if a CI config exists, its pytest step runs the whole `tests/` tree with no file or `-k` filter.
- Rule 2, no retries: no rerun/flaky plugin in `pyproject.toml`, no `--reruns`, no `@pytest.mark.flaky`, no retry loops around assertions; every `skip`/`skipif` carries a reason and every `xfail` is `strict=True`.
- Rule 3, no one-off scripts: every `src/*.py` has a `FILES.md` line, a `reference/scripts.md` entry, and at least one `tests/` file that references it.
- Fix whatever the first run finds (undocumented or untested `src/` scripts, bare skips).

## Capabilities

### New Capabilities
- `process-hygiene`: repo-level invariants on how tests are collected and retried and on what may live in `src/`, enforced by a test.

### Modified Capabilities
<!-- none: claude-md-script-index defines where scripts are documented; this adds a check, not a new place -->

## Impact

- New: `tests/test_process_hygiene.py`; `FILES.md` line for it.
- Possibly edited: `FILES.md`, `reference/scripts.md`, test files with bare skips, to clear first-run findings.
- No change to pipeline behavior, JSON contracts or `src/`.
- Out of scope: adding a CI workflow (none exists; Rule 1's CI clause is conditional on one appearing), flaky-test detection by rerun, `/retrofit`.
