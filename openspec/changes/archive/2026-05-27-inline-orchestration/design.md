## Context

`orchestrate.py` is a 600-line Python script that implements the phase 3 build loop. It loads `BUILD_PLAN.json`, renders part prompts from templates, calls `claude -p <prompt>` as a subprocess for each part, runs `run_cadquery_model.py` to validate geometry, and retries on failure up to `--max-retries` times. On retry exhaustion it blocks on `input()` prompting for skip/abort/hint.

The problem: every `claude -p` invocation is a cold start. The subprocess receives only what fits in the rendered prompt -- template variables, error context from the previous attempt, and reference content. It has no access to the planning conversation: why certain dimensions were chosen, what the user prioritized, what alternatives were discussed. Corrections are made blind.

Because the skill is always used interactively (a human runs `/cq-design` in a Claude session), Claude is already present and can execute the loop itself. The subprocess layer exists to work around the assumption that Claude is not the session.

## Goals / Non-Goals

**Goals:**
- Remove `orchestrate.py` and `_call_claude()` entirely
- Move the part loop into SKILL.md as Claude-executable prose instructions
- Preserve the same external behavior: same output files, same retry limit, same quality gate
- Conversational failure handling instead of terminal `input()` prompt
- Claude writes block imports directly; no post-processing injection

**Non-Goals:**
- Changing `run_cadquery_model.py` or its JSON contract
- Changing the quality gate, plan validator, or any block/exporter code
- Supporting unattended/CI execution (explicitly out of scope per design decision)
- Changing what gets exported or how the user receives output

## Decisions

### Decision: Delete orchestrate.py entirely (no CI shim)

**Chosen:** Hard delete. No "headless" wrapper script retained.

**Alternatives considered:**
- Keep a stripped `orchestrate.py` that drives the loop without calling `claude -p` (just shell commands). Rejected: adds maintenance surface for a use case that doesn't exist.
- Keep it for CI. Rejected: CI is not a real scenario for this skill (confirmed by user). Keeping dead code for a hypothetical use case is worse than the cost of adding it back if needed.

### Decision: Block imports written directly by Claude, not injected

**Chosen:** SKILL.md instructs Claude to include `from blocks import <function>` statements at the top of each generated script, based on `blocks_needed` from the plan.

**Alternatives considered:**
- Keep `_prepend_block_imports` as a standalone utility called via Bash. Rejected: unnecessary indirection. The blocks_needed list is in the plan, which Claude already reads. Writing the imports directly is simpler and keeps the generated script complete as written.

**Note:** The constraint `# Do not write import statements for block functions` in SKILL.md must be removed. It was written for the orchestrator-injected-imports model.

### Decision: Retry loop in SKILL.md prose, not code

**Chosen:** SKILL.md phase 3 describes the retry loop in structured prose (numbered steps, explicit loop with counter, failure handling). Claude executes it as tool calls: Write the script, Bash to run the validator, parse JSON, iterate.

**Rationale:** Claude retains full session context across retries. When fixing a non-manifold edge error on attempt 2, Claude knows the user wanted a press-fit snap hook, knows the wall thickness constraint, knows what was discussed in planning. The correction is informed by intent, not just error messages.

**Risk:** Claude might not follow the prose loop precisely on every run. This is mitigated by writing the phase 3 instructions as an explicit numbered algorithm with clear entry/exit conditions, not free-form guidance.

### Decision: Failure handling via conversation, not terminal input()

**Chosen:** When retries are exhausted, SKILL.md instructs Claude to summarize what failed and ask the user in-session what to do (skip, try a different approach, provide a hint).

**Alternatives considered:**
- Keep a terminal prompt. Rejected: doesn't work in Claude Code's session model and was identified as unneeded by the user.

## Risks / Trade-offs

**Context accumulation in long builds**
For a 3-part build with 3 retries each, Claude might generate/read ~9 CadQuery scripts in one session. Each script is ~100-300 lines. This is well within context limits for the expected build size (max 3 parts, mean 1).
Mitigation: None required at this scale.

**Prompt discipline for the loop**
The part loop relies on Claude following numbered instructions precisely: write script, run validator, check JSON, decide, loop. This is less mechanically reliable than Python code.
Mitigation: Phase 3 instructions written as an algorithm with explicit conditions ("if `success` is true AND no blocking errors, advance to next part; otherwise..."). Include the JSON field names Claude must check.

**Build log**
`orchestrate.py` wrote an incremental `build_log.json` as each part completed. Inline, Claude produces a conversational summary instead. This is a slight regression for users who wanted a machine-readable log.
Mitigation: After all parts complete, Claude can write a simple `build_log.json` to the build directory if needed. Not blocked on this change.

## Migration Plan

1. Delete `src/orchestrate.py`
2. Delete `tests/test_orchestrate.py`
3. Rewrite SKILL.md phase 3: remove "run orchestrate.py" section, add inline part-loop algorithm
4. Remove the "Do not write import statements for block functions" constraint from SKILL.md generated-script rules
5. Archive `openspec/specs/orchestration-loop/spec.md` and `openspec/specs/robust-claude-subprocess/spec.md`

No rollback complexity -- the deleted files are in version control. Rollback is `git revert`.

## Open Questions

- Should Claude still write a `build_log.json` for structured tracking, or is the conversational summary sufficient? (Deferred -- not blocking.)
