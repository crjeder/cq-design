## Context

Phase 2's current loop (`skill/phase2_planning.md`):

1. Main renders `build/planning_prompt.txt`, spawns the planner agent, and receives the
   plan JSON as its final message.
2. Main writes that JSON to `BUILD_PLAN.json` (indent 2).
3. Main runs `plan_validate.py BUILD_PLAN.json`.
4. On rejection, main resumes the planner agent with the error list and repeats from step
   1's result.
5. Once valid, main runs `plan_summary.py` and shows it to the user.

Every round trip through steps 1-4 pushes the full plan JSON through the main session's
context, even though nothing in the main session reads that JSON directly -- only
`plan_summary.py`'s rendering (step 5) and `plan_validate.py`'s CLI (step 3) ever consume
it, and both already work from the file on disk. The builder agent (Phase 3) does not have
this problem: it writes its script, lints, validates, and renders inside its own Bash
loop, and only leaves the agent boundary once per part, with a small structured result.
The planner should follow the same shape.

## Goals / Non-Goals

**Goals:**
- Planner agent owns the write-validate-retry loop for `BUILD_PLAN.json`, using Bash
  exactly like the builder agent already does for part scripts.
- Main session's Phase 2 role shrinks to: render the prompt, spawn the agent once, run
  `plan_summary.py` against the resulting file, and resume the agent only when a user
  decision needs to flow back in (an open question answer, or a requested edit after the
  checkpoint).
- No change to `plan_validate.py`, `plan_summary.py`, or the `BUILD_PLAN.json` schema.

**Non-Goals:**
- Not changing what counts as a valid plan, or the rules planner follows to produce one.
- Not changing the user-facing Phase 2 checkpoint (plan summary, open questions, design
  proposals) -- only where the validation loop that precedes it runs.
- Not touching Phase 0/1/3/4 agents or the builder/auditor loop.

## Decisions

**The planner retries against its own `plan_validate.py` output, bounded, before
returning.** Mirrors the builder's "write, lint, validate, render" internal loop (Phase 3
already does this with a 3-attempt cap). The planner's prompt gets an equivalent
instruction: write `BUILD_PLAN.json`, run `plan_validate.py`, and on any error, fix and
retry, up to a small bounded number of attempts (align with the builder's 3-attempt
convention so the two loops read the same way in the docs). If still invalid after the
cap, it returns `blocked` with the remaining validator errors -- this is the same
"blocked after N attempts -> main asks the user" shape Phase 3 already uses, reused rather
than inventing a second escalation pattern.

Alternative considered: unbounded retry inside the agent. Rejected -- an unbounded loop
with no escalation path can spin on a validator error the planner keeps regenerating
wrong (e.g. a genuinely ambiguous schema requirement), burning agent turns with no
main-session visibility. A bounded loop with a `blocked` escalation matches the existing
builder pattern and gives the user a way back in.

**Return contract: status summary, not JSON text.** The agent's final message becomes a
small structured summary: validity, part count, and (if any) the open items that need a
user decision -- the same open items `plan_summary.py` already extracts from
`planning_notes` (`OPEN:` markers) plus any validator errors that survived the retry cap.
The main session never parses plan content out of the agent's reply; it reads the file.

Alternative considered: agent still returns the full JSON *and* writes the file, so main
has a fallback if the file write failed. Rejected as redundant -- a failed disk write is
itself a failure the agent should report (`blocked`/error), not silently paper over by
having main re-write from the reply. Matches how the builder agent already treats a
failed render.

**User-decision escalation reuses "resume the same agent".** When the planner needs a
user decision (an unverifiable dimension, an unclear fit -- see `planning-decision-scope`
-- or validator errors it could not resolve within the retry cap), it returns `blocked`
with the specific question(s). Main asks the user and resumes the *same* planner agent
with the answer, exactly as Phase 3's hint-after-exhaustion pattern resumes the same
builder. No second agent is spawned.

**Plan summary checkpoint reads the file, not the agent reply, even on success.** Whether
the planner returns `valid` or `blocked`-then-resolved, main's next action is always
`plan_summary.py BUILD_PLAN.json` against the on-disk file. This keeps one code path for
"how does main show the plan" regardless of how many internal retries the planner needed.

## Risks / Trade-offs

- **Planner error-fixing quality inside the loop is unverified.** The builder pattern
  already proves an agent can iterate against a typed validator's errors; `plan_validate.py`
  already emits errors naming the part/field, so the planner has the same signal quality
  the builder gets from `run_cadquery_model.py`. Mitigation: keep the retry cap low (match
  the builder's 3) so a genuinely stuck planner escalates quickly instead of burning turns.
- **Losing the raw-JSON fallback in main's context.** If `plan_summary.py` has a rendering
  bug, main previously still had the raw JSON in its own context to fall back on for
  debugging. Mitigation: none needed -- main can `Read BUILD_PLAN.json` directly off disk
  on demand; it is never deleted, just no longer pushed into context by default.
- **Prompt/doc drift between phase2 and phase3 wording.** Reusing the builder's
  attempt-cap and blocked-escalation language in `skill/phase2_planning.md` needs to stay
  literally consistent with `skill/phase3_build.md`'s so a future edit to one pattern
  doesn't silently diverge from the other.

## Migration Plan

Documentation/prompt-only change (`skill/phase2_planning.md`, planner spawn instruction).
No data migration, no schema version bump, no feature flag: the next Phase 2 run picks up
the new instruction. Rollback is reverting those files.

## Open Questions

None -- scope is confined to the planner's own write/validate/retry loop and its return
contract; no schema or validator changes are involved.
