## 1. SKILL.md - Establish SKILL_DIR and fix script invocations

- [x] 1.1 Add a `SKILL_DIR` setup block at the top of the Phase 1 prerequisites section that resolves to the absolute path of the directory containing SKILL.md
- [x] 1.2 Replace all `python src/plan_validate.py` invocations with `python "$SKILL_DIR/src/plan_validate.py"`
- [x] 1.3 Replace all `python src/orchestrate.py` invocations with `python "$SKILL_DIR/src/orchestrate.py"`
- [x] 1.4 Replace all other bare `src/` script references (quality_gate, preview, etc.) with `$SKILL_DIR/src/` equivalents
- [x] 1.5 Provide Windows-compatible equivalent (`$SKILL_DIR` via `python -c "import pathlib, sys; print(pathlib.Path(sys.argv[1]).parent.resolve())" "$0"` or similar) alongside the POSIX form

## 2. SKILL.md - Artefact path display

- [x] 2.1 Update the "Written to" confirmation message after plan write to display the absolute path (not just `BUILD_PLAN.json`)
- [x] 2.2 Update the build output section to clarify that `build/` is created in the caller's cwd

## 3. src/orchestrate.py - Anchor reference file paths to script location

- [x] 3.1 Replace any relative-path references to `reference/` files with `Path(__file__).parent.parent / "reference" / ...` so they resolve correctly regardless of cwd
- [x] 3.2 Replace any relative-path references to `prompts/` files with `Path(__file__).parent.parent / "prompts" / ...`
- [x] 3.3 Verify `--output-dir` default (`build/`) remains relative to cwd (no change needed if already unqualified)
- [x] 3.4 Verify `build_log.json` is written relative to cwd, not the script's location

## 4. src/plan_validate.py - Verify path argument handling

- [x] 4.1 Confirm `plan_validate.py` treats the positional plan-path argument as-is (no forced resolution relative to script location) -- document with a one-line comment if the behavior is non-obvious

## 5. Tests

- [x] 5.1 Add a test in `test_orchestrate.py` that mocks a cwd different from the skill root and verifies reference files are still loaded (via `Path(__file__)` resolution)
- [x] 5.2 Add a test that verifies `build_log.json` is written to the mocked cwd, not the script directory
