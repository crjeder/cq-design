## 1. Guard tests first

- [x] 1.1 In `tests/test_prose_layer.py`, add a parametrized test over `SKILL.md`, `commands/*.md`, `skill/*.md`, `prompts/*.md`, `reference/*.md` that fails on `install.sh`, `install.ps1`, `openspec/`, `tests/`, `evals/`, `documentation/`, `TODO.md`, `FILES.md`, `CLAUDE.md`, or a backticked token equal to an `openspec/specs/` directory name; confirm it fails on the current tree with the known hits
- [x] 1.2 Add an installer-parity test that regex-parses `ALLOWLIST=(...)` from `install.sh` and `$Allowlist = @(...)` from `install.ps1` and asserts equal sets

## 2. Move runtime data out of dev directories

- [x] 2.1 `git mv evals/model_prices.json src/model_prices.json`; update `src/session_cost.py` (`_PRICES_PATH`, module docstring) and `evals/run_evals.py`
- [x] 2.2 `git mv documentation/Block_Sources.md reference/Block_Sources.md`; update `src/render_prompt.py` (path + docstring) and the README link
- [x] 2.3 Run `uv run pytest tests/test_render_prompt.py tests/test_run_evals.py` plus any session-cost test; fix path assertions

## 3. Fix shipped prose

- [x] 3.1 `skill/phase3_build.md`: `planning-phase` -> `prompts/planning.md` rule 10; `fem-wall-shell-solve` / `fem-stress-advisor` -> `reference/scripts.md`'s `src/fem_check.py` row (or drop); `quality-gate-fix-policy` -> `skill/phase4_deliver.md` step 1
- [x] 3.2 `skill/phase4_deliver.md:28` and `reference/FDM 3D Print Design Guidelines.md:53`: `toolpath-speed-advisor` -> `reference/scripts.md`'s `src/toolpath_speed.py` row
- [x] 3.3 `SKILL.md:14`: "an installer copy" instead of naming `install.sh` / `install.ps1`; `skill/resume.md:85`: "reinstall from the repo"
- [x] 3.4 `reference/scripts.md`: drop `evals/` and `CLAUDE.md` from the header, remove the `tests/test_build_script.py` parenthetical and the `src/log.py` row's `tests/` hit, point the `session_cost.py` row at `src/model_prices.json`, and move the `evals/run_evals.py` row verbatim into a new `evals/README.md`
- [x] 3.5 `src/skill_version.py` docstring: "the repo's installer" wording (optional consistency) -- skipped: docstring names the installers' own flags accurately for developers
- [x] 3.6 Run `uv run pytest tests/test_prose_layer.py`; the new guard passes

## 4. Installer allowlist

- [x] 4.1 `install.sh`: replace `EXCLUDES` and the rsync/tar branch with `ALLOWLIST=(SKILL.md .claude-plugin commands skill prompts reference src templates pyproject.toml uv.lock .python-version LICENSE)`, `cp -R` each entry that exists, then prune `__pycache__`, `*.egg-info`, `.fossil` under the destination
- [x] 4.2 `install.ps1`: replace `$Excludes` with `$Allowlist` (same entries), `Copy-Item` each existing entry, extend the recursive prune to `*.egg-info` and `.fossil`
- [x] 4.3 Update the usage/help text of both installers if it describes what is copied
- [x] 4.4 Run `install.ps1 -Dest <scratch>` and `install.sh --dest <scratch>` (Git Bash); confirm the destination holds exactly the allowlist, no `src/*.egg-info` / `src/.fossil`, `uv sync` succeeds, and `uv run --project <dest> python <dest>/src/session_cost.py --help` and `render_prompt.py sourcing` run

## 5. Single layout tree

- [x] 5.1 Replace `FILES.md` content with CLAUDE.md's current `File Layout` tree (update the moved `model_prices.json` / `Block_Sources.md` lines and add `evals/README.md`)
- [x] 5.2 Replace the tree in `CLAUDE.md`'s `File Layout` section with a pointer to `FILES.md`, keeping the `reference/scripts.md` pointer; mention `evals/README.md` for eval contracts

## 6. Verify

- [x] 6.1 `uv run pytest tests/test_prose_layer.py tests/test_plan.py tests/test_render_prompt.py tests/test_run_evals.py` green
- [x] 6.2 `openspec validate trim-installed-skill` passes
