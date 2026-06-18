## Context

`_call_claude()` in `src/orchestrate.py` invokes `claude -p <prompt>` via `subprocess.run()`. The current implementation has three reliability gaps when run non-interactively (e.g., as a background task from a Claude Code skill):

1. `subprocess.TimeoutExpired` is not caught -- it propagates to the top level and crashes the orchestrator with an unhandled exception.
2. Stdin is inherited from the parent process -- if `claude -p` blocks on any interactive prompt (first-run setup, auth, permission confirmation), the subprocess hangs until the 300 s timeout fires, but the timeout itself is also unhandled, so the crash still occurs.
3. The prompt is passed as a positional CLI argument -- on Windows, argument strings over ~32 KB can fail silently or be truncated. The rendered part prompt (template + 15 KB CQ reference + part spec) can approach this limit.

## Goals / Non-Goals

**Goals:**
- `claude -p` failures are always caught and converted to a `RuntimeError` so the retry loop handles them cleanly.
- The subprocess never blocks on interactive input.
- Prompts of any practical size are delivered reliably.
- The timeout is configurable without a code change.

**Non-Goals:**
- Changing the retry logic, JSON contract, exit codes, or any other orchestrator behaviour.
- Supporting alternative LLM backends.
- Fixing anything in `quality_gate.py` (which also calls `claude -p` but is outside scope here).

## Decisions

### Prompt delivery via stdin rather than positional argument

Pass the prompt as stdin to `claude -p` instead of as a positional argument. This eliminates the Windows CLI arg length limit entirely and is cleaner for large strings.

**Implementation:**
```python
result = subprocess.run(
    ["claude", "-p", "--dangerously-skip-permissions"],
    input=prompt_text,
    capture_output=True,
    text=True,
    timeout=timeout_s,
)
```

*Alternatives considered:*
- Write to a temp file and pass the path: works, but adds file I/O and cleanup logic.
- Keep positional arg and add truncation guard: hides the real problem.

### `--dangerously-skip-permissions` flag

Add this flag so the child `claude` process never pauses for interactive permission approval in non-interactive environments. Without it, any new tool or permission the child needs can cause an indefinite hang.

*Risk:* The flag bypasses permission confirmations. This is acceptable here because the child `claude -p` call is generating CadQuery Python code -- it has no tool access that could cause side effects beyond writing to stdout.

### Catch `subprocess.TimeoutExpired`

Wrap the `subprocess.run` call to catch both `RuntimeError` and `subprocess.TimeoutExpired`, converting both to a uniform `RuntimeError` that the existing retry loop already handles.

### Configurable timeout via `CLAUDE_TIMEOUT` env var

Default 600 s (doubled from current 300 s). Readable from `os.environ.get("CLAUDE_TIMEOUT", "600")` at call time. No new CLI flags needed.

## Risks / Trade-offs

- `--dangerously-skip-permissions` may not exist or may have a different name in older Claude Code versions. Risk: the subprocess will fail with a bad-flag error on first attempt. Mitigation: the existing retry loop handles this failure gracefully; users on older versions will see a clear error message rather than a hang.
- Passing the prompt via stdin assumes `claude -p` reads from stdin when no positional prompt is given. This is standard CLI convention but should be verified in the test suite.

## Migration Plan

Single-function change to `_call_claude()`. No data migrations, no API changes. Rollback is reverting the function body.
