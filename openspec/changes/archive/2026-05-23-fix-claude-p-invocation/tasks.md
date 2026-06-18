## 1. Fix orchestrate.py

- [x] 1.1 Remove `import tempfile` if it becomes unused after the change (check other uses first)
- [x] 1.2 Rewrite `_call_claude` in `src/orchestrate.py`: remove the `NamedTemporaryFile` write, `os.unlink`, and `finally` block; pass `prompt_text` directly as the `-p` argument

## 2. Fix quality_gate.py

- [x] 2.1 Remove `import tempfile` if it becomes unused after the change (check other uses first)
- [x] 2.2 Rewrite `_call_claude` in `src/quality_gate.py`: same change as 1.2

## 3. Update spec

- [x] 3.1 Update `openspec/specs/orchestration-loop/spec.md` requirement wording from `claude -p <rendered_prompt_file>` to `claude -p <prompt_text>` (inline string, no file intermediary), applying the delta from the change spec

## 4. Verify

- [x] 4.1 Run `uv run pytest tests/test_orchestrate.py` -- all tests should pass without modification (they mock `_call_claude`)
- [x] 4.2 Smoke-test with a real `claude` binary: run `orchestrate.py` against a minimal single-part `BUILD_PLAN.json` and confirm the generated `.py` file contains Python code, not prose
