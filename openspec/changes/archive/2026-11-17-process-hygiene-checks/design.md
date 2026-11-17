## Context

No `.github/` or other CI config exists; `pytest` with `testpaths = ["tests"]` is the only gate. `claude-md-script-index` already requires each `src/` script in `FILES.md` and `reference/scripts.md`, but nothing verifies it. The text-to-cad rules are cheap to state and cheap to check mechanically.

## Goals / Non-Goals

**Goals:**
- One fast test module (no CadQuery import) that turns the three rules into failures.
- Failure messages name the file and line so the fix is obvious.

**Non-Goals:**
- Writing a CI workflow, detecting flakiness by rerun, or retrofitting in-flight projects.
- Judging test quality; only collection, retries and script registration.

## Decisions

- **A test, not a `src/` script.** CLAUDE.md sends checkable work to a script with a JSON contract, but this is a repo invariant, not a pipeline tool: no phase or user calls it. A `src/hygiene.py` would itself be a one-off helper. Alternative (script + test) rejected as speculative.
- **Static text/AST checks.** Read `pyproject.toml` with `tomllib` (3.11+) or a regex fallback, since `requires-python` includes 3.10; parse test files with `ast` to find `skip`/`skipif`/`xfail` decorators and `pytest.mark.flaky`. Alternative: `pytest --collect-only` diffed against the file list; rejected because it imports CadQuery and takes seconds.
- **Retry loops:** flag only a `for`/`while` containing `try` with `except AssertionError`; a broader heuristic would false-positive.
- **Script registration by name match.** Module name must appear in `FILES.md`, in `reference/scripts.md`, and in some `tests/*.py`. Cheap, and catches the real failure (a script added and forgotten). A small explicit allowlist covers legitimate exceptions.
- **CI clause conditional.** Glob `.github/workflows/*.y*ml`, `.gitlab-ci.yml`, `azure-pipelines.yml`; for each `pytest` invocation line, reject a path ending `.py` or a `-k` flag.

## Risks / Trade-offs

- [Name match is loose: a short stem like `log` matches unrelated text] -> match `log.py` / `import log` / `src/log` forms, not the bare stem.
- [First run fails on the existing repo] -> clearing findings is part of the task list, not deferred.
- [No CI means Rule 1's CI clause is dormant] -> stated in the spec; it activates when a workflow is added.
