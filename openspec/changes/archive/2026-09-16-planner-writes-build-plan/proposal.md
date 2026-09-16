## Why

Phase 2 today has the planner agent return the entire `BUILD_PLAN.json` as its final
message; the main session parses that text, writes it to disk, shells out to
`plan_validate.py`, and on any schema/inventory error resumes the planner with the error
list, repeating until it validates. The full plan JSON (which can be large -- many parts,
interfaces, `planning_notes`) round-trips through the main session's context on every
validation cycle even though the main session never inspects the JSON itself, only
`plan_summary.py`'s rendering of the file on disk. The planner agent already runs with
Bash access (same as the builder and research agents); it can write and validate its own
output the way builder agents already write-lint-validate-render in one internal loop.

## What Changes

- The planner agent writes `BUILD_PLAN.json` to the working directory itself and runs
  `plan_validate.py` itself, retrying internally against its own validation errors instead
  of being resumed by the main session for each rejection.
- The planner agent returns a short status message instead of the plan JSON: validity,
  part count, and any items that need a user decision (an unverifiable dimension, an
  unclear fit, or a validation error it cannot resolve on its own after retrying).
- The main session no longer parses or writes the plan JSON; it runs `plan_summary.py`
  directly against the file the planner already wrote, and only resumes the planner agent
  when there is a genuine user decision to feed back (open question answered, or a
  requested edit after the Phase 2 checkpoint).
- **BREAKING** (internal contract only, no user-facing behavior change): the planner
  agent's return contract changes from "final message is the plan JSON" to "final message
  is a status summary; the plan lives on disk". Anything that resumed the planner
  expecting to receive JSON text must instead read `BUILD_PLAN.json` from disk.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `subagent-orchestration`: the "Planner runs as a strong-model agent" requirement changes
  from "`plan_validate.py` gating ... remain[s] in the main session; validation errors
  re-enter the planner agent" to the planner running its own write/validate/retry loop and
  returning a status summary; the main session's role narrows to spawning the agent once,
  running `plan_summary.py` against the resulting file, and resuming the agent only for a
  user decision.
- `plan-disk-write`: the actor performing the write from "the skill" (main session,
  writing text it parsed from the agent's reply) to the planner agent itself, writing the
  file directly via Bash before returning. The on-disk outcome (path, contents, timing
  relative to user review) is unchanged.

## Impact

- `skill/phase2_planning.md`: rewrite the planner invocation and validation-loop steps.
- `prompts/planning.md` (or the agent spawn instruction that wraps it): instruct the
  planner to write, validate, and retry itself, and define its new return contract.
- No changes to `src/plan_validate.py`, `src/plan_summary.py`, or `BUILD_PLAN.json`'s
  schema -- this is a workflow/prompt change, not a schema or validator change.
