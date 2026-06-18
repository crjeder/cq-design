## 1. Project Metadata

- [x] 1.1 Create `pyproject.toml` with `[project]` name, version, `requires-python = ">=3.10,<3.13"`, and all runtime deps from `requirements.txt`
- [x] 1.2 Add `[tool.uv.sources]` entry for `cq-warehouse` pointing to the git repo
- [x] 1.3 Add `[dependency-groups]` dev group with `pytest>=7,<9`
- [x] 1.4 Add `[tool.uv] package = false` to mark this as a non-publishable tool project
- [x] 1.5 Add `[tool.pytest.ini_options]` with `testpaths = ["tests"]`

## 2. Python Version Pin

- [x] 2.1 Create `.python-version` containing `3.12`

## 3. Lockfile

- [x] 3.1 Run `uv lock` to generate `uv.lock`
- [x] 3.2 Verify `uv.lock` contains the `cq-warehouse` entry with a pinned git commit SHA

## 4. Verification

- [x] 4.1 Run `uv sync` and confirm it completes without errors
- [x] 4.2 Run `uv run pytest tests/test_orchestrate.py tests/test_plan_validate.py` (fast, no CadQuery) and confirm all pass

## 5. Cleanup

- [x] 5.1 Delete `requirements.txt`

## 6. Documentation

- [x] 6.1 Replace the `## Dependencies` section in `README.md` with a `## Setup` section using `uv sync` instructions
- [x] 6.2 Update the setup block in `CLAUDE.md` to use `uv sync` and `uv run pytest`
