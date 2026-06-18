## Why

The build phase (phase 3) currently runs via `orchestrate.py`, a Python script whose sole purpose is to call `claude -p` in a loop. Each `claude -p` invocation is a context-blind subprocess: it receives only a rendered prompt string and has no access to the planning conversation, user intent, or anything decided in phases 1-2. When corrections are needed, the subprocess reasons from error messages alone. Since the skill is always run interactively with Claude as the session, this middle layer is redundant indirection -- Claude can run the part loop itself, with full context.

## What Changes

- **DELETE** `src/orchestrate.py` -- the Python orchestration loop is removed entirely
- **DELETE** `tests/test_orchestrate.py` -- tests for the deleted script
- **EXPAND** SKILL.md phase 3 section with inline instructions: Claude reads `BUILD_PLAN.json`, writes each part script, runs `run_cadquery_model.py` via Bash, parses JSON results, and iterates with corrections up to 3 retries
- **REMOVE** block-import injection from the orchestrator -- Claude writes correct `from blocks import ...` statements directly when generating part scripts; the orchestrator's `_prepend_block_imports` hack is no longer needed
- **REPLACE** terminal skip/abort/hint prompt with conversational failure handling -- when retries are exhausted Claude explains the situation to the user and asks how to proceed in-session
- **KEEP** `src/run_cadquery_model.py`, `src/quality_gate.py`, `src/plan_validate.py` unchanged -- these are tool boundaries, not orchestration

No behavior visible to the user changes. The build still produces the same output files. Error messages and retry logic work the same way, just driven by Claude instead of Python.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `orchestration-loop`: All requirements are removed. The orchestrator script no longer exists; its responsibilities move into SKILL.md prose instructions executed by Claude inline.
- `robust-claude-subprocess`: All requirements are removed. There is no `_call_claude()` function; Claude does not launch itself as a subprocess.

## Impact

- `src/orchestrate.py` deleted
- `tests/test_orchestrate.py` deleted
- `SKILL.md` phase 3 section substantially rewritten
- `openspec/specs/orchestration-loop/spec.md` archived or deleted
- `openspec/specs/robust-claude-subprocess/spec.md` archived or deleted
- No changes to `run_cadquery_model.py`, `quality_gate.py`, `plan_validate.py`, or any block/exporter code
