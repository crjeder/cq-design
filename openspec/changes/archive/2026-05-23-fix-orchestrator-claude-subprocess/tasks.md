## 1. Rewrite `_call_claude()`

- [x] 1.1 Read `CLAUDE_TIMEOUT` env var; default to 600 if absent or non-numeric
- [x] 1.2 Change `subprocess.run` call: remove positional prompt arg, add `--dangerously-skip-permissions`, pass prompt via `input=prompt_text`, set `stdin=subprocess.PIPE`
- [x] 1.3 Wrap `subprocess.run` to catch `subprocess.TimeoutExpired` and re-raise as `RuntimeError` with "timeout" in the message

## 2. Update tests

- [x] 2.1 Add test: `subprocess.TimeoutExpired` from the mock is caught and the part-loop records a failed attempt (no unhandled exception)
- [x] 2.2 Add test: `CLAUDE_TIMEOUT=120` env var is forwarded as the timeout value to `subprocess.run`
- [x] 2.3 Add test: prompt is passed via `input=` kwarg, not as a positional CLI argument
- [x] 2.4 Add test: `--dangerously-skip-permissions` is present in the command list

## 3. Verify

- [x] 3.1 Run `uv run pytest tests/test_orchestrate.py` -- all tests pass
- [x] 3.2 Run `uv run pytest tests/` -- no regressions
