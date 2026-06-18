## Why

`_call_claude` in both `orchestrate.py` and `quality_gate.py` writes the rendered prompt to a temp file, then passes the **file path** as the argument to `claude -p`. The Claude Code CLI's `-p`/`--print` flag treats its argument as literal prompt text, not as a path to read -- so Claude receives a bare temp-file path (e.g. `/tmp/tmpXXXXXX.md`) as its entire prompt and responds with prose instead of code. Every call site in both scripts shares this defect.

## What Changes

- Remove the temp-file write in `_call_claude` in both files; pass `prompt_text` directly as the `-p` argument via `subprocess.run`
- The `tempfile.NamedTemporaryFile` + `os.unlink` scaffolding is eliminated from both functions
- No change to callers, retry logic, prompt rendering, or `_extract_python`

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `orchestration-loop`: The requirement currently reads `claude -p <rendered_prompt_file>` -- change to `claude -p <prompt_text>` (inline string, no file intermediary)

## Impact

- `src/orchestrate.py` -- `_call_claude` function only
- `src/quality_gate.py` -- `_call_claude` function only
- `openspec/specs/orchestration-loop/spec.md` -- requirement wording update
- No API, schema, or test contract changes; `test_orchestrate.py` already mocks `_call_claude` directly so tests are unaffected
