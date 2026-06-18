## Context

`_call_claude` exists in two files (`src/orchestrate.py` and `src/quality_gate.py`) as a near-identical helper. Both write the rendered prompt to a `tempfile.NamedTemporaryFile`, then pass the **path** to `claude -p`. Because `claude -p` treats its argument as literal prompt text (not as a path to read), Claude receives a bare temp-file path as its entire prompt and responds with prose.

## Goals / Non-Goals

**Goals:**
- Pass prompt text directly to `claude -p` so Claude receives the actual rendered prompt
- Eliminate the temp-file write/delete cycle from both `_call_claude` implementations

**Non-Goals:**
- Deduplicating the two `_call_claude` functions into a shared module (separate concern)
- Changing retry logic, prompt rendering, or `_extract_python`
- Any changes to callers or tests (tests already mock `_call_claude` directly)

## Decisions

### Pass prompt text as the `-p` argument directly

Replace:
```python
with tempfile.NamedTemporaryFile(...) as tf:
    tf.write(prompt_text)
    prompt_path = tf.name
subprocess.run(["claude", "-p", prompt_path], ...)
```
With:
```python
subprocess.run(["claude", "-p", prompt_text], ...)
```

**Why not stdin piping?** The CLI supports `-p <text>` as the documented non-interactive mode. Stdin piping would require knowing whether `claude` reads stdin without `-p`, which is less certain. Direct argument is the documented path.

**Why not a shared module?** The two functions are identical but duplication is confined to two files and a trivial helper. Extracting a shared `_call_claude` into a new module would require changes to imports, tests, and PYTHONPATH. Not worth the churn for a two-line fix.

**Command-line length:** `subprocess.run` with a list bypasses the shell and calls `CreateProcess` (Windows) or `execve` (POSIX) directly. Windows `CreateProcess` has a ~32 KB limit on the total argument string. Rendered prompts with full CQ reference injected can exceed this. If that limit is hit in practice, the mitigation is to pipe via stdin -- but this is an observable failure (subprocess raises `OSError`) rather than a silent one, so it can be addressed if it occurs.

## Risks / Trade-offs

- **Windows command-line length limit** → If a rendered prompt exceeds ~32 KB total, `subprocess.run` will raise `OSError`. Mitigation: monitor; fall back to stdin pipe if needed. Current prompts with CQ reference are large but the limit is generous.
- **No test coverage of the actual subprocess call** → The fix is unverifiable by the existing mock-based tests. A manual smoke test against a real `claude` binary is needed after the change.

## Migration Plan

1. Edit `_call_claude` in `src/orchestrate.py` -- remove temp file, pass text directly
2. Edit `_call_claude` in `src/quality_gate.py` -- same change
3. Update `openspec/specs/orchestration-loop/spec.md` requirement wording
4. Run existing tests (all pass without change since `_call_claude` is mocked)
5. Smoke-test with a real `claude` binary against a minimal `BUILD_PLAN.json`

Rollback: revert both source files; no database or schema migration involved.
