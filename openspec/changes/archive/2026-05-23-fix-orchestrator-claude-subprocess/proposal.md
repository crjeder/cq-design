## Why

The orchestrator crashes with an unhandled `subprocess.TimeoutExpired` when `claude -p` exceeds 300 seconds, and can hang indefinitely when the child process inherits an open stdin and blocks on an interactive prompt. Together these make the build pipeline fragile in non-interactive (background task) environments.

## What Changes

- Catch `subprocess.TimeoutExpired` in `_call_claude()` alongside `RuntimeError`, so a timeout is treated as a recoverable call failure rather than a crash.
- Close stdin on the child `claude` process (`stdin=subprocess.DEVNULL`) to prevent indefinite hangs on interactive prompts.
- Pass the prompt via stdin rather than as a positional CLI argument to avoid Windows command-line length limits (~32 767 chars) on large prompts.
- Add `--dangerously-skip-permissions` to the `claude -p` invocation so the child process never blocks on a permission confirmation in a non-interactive context.
- Make the per-call timeout configurable (env var `CLAUDE_TIMEOUT`, default 600 s) to accommodate large prompts on slow connections.

## Capabilities

### New Capabilities

- `robust-claude-subprocess`: Reliable non-interactive invocation of `claude -p` from the orchestrator subprocess, including timeout handling, stdin hygiene, and prompt delivery via stdin.

### Modified Capabilities

<!-- none - no existing spec-level behavior changes -->

## Impact

- `src/orchestrate.py` - `_call_claude()` function rewritten
- No changes to the JSON contract, exit codes, or retry logic
- No new dependencies
