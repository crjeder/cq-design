## 1. Planner spawn instruction

- [x] 1.1 In `skill/phase2_planning.md`, rewrite the planner agent spawn step: instruct the
      agent to write `BUILD_PLAN.json` (indent 2) to the working directory itself, run
      `uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/plan_validate.py" BUILD_PLAN.json`
      itself, and on any error fix and retry inside the same agent invocation, up to a
      bounded attempt cap (match the builder's 3-attempt convention).
- [x] 1.2 Define the agent's new return contract in the same section: on success, a status
      summary (validity, part count, no open items or the count of open items); on
      exhausted retries, `blocked` plus the remaining `plan_validate.py` errors and/or the
      unresolved user-facing questions (unverifiable dimension, unclear fit -- see
      `planning-decision-scope`).
- [x] 1.3 Remove the old steps describing main writing `BUILD_PLAN.json` from the agent's
      reply text and main running `plan_validate.py` directly.

## 2. Main-session loop

- [x] 2.1 Update the resume/rejection step: main resumes the planner agent only when the
      agent returned `blocked` with a user-facing question, after collecting the user's
      answer -- never merely to relay a validator error the agent already saw.
- [x] 2.2 Confirm the "plan summary checkpoint" step already runs `plan_summary.py`
      against the on-disk `BUILD_PLAN.json` regardless of agent status (valid immediately,
      or valid after a resumed round) -- adjust wording only if it currently assumes main
      wrote the file.
- [x] 2.3 Confirm the journal line (`- phase2/plan_written: BUILD_PLAN.json validated, <n>
      parts`) is still appended by main after the agent's final `valid` status, sourcing
      `<n>` from the summary or from re-reading the file -- not from parsing agent JSON
      text.

## 3. Consistency check

- [x] 3.1 Re-read `skill/phase3_build.md`'s attempt-cap and blocked-escalation wording and
      confirm the Phase 2 wording added in Task 1 matches it (same cap language, same
      `blocked`-then-resume shape) so the two loops read as one pattern applied twice.
- [x] 3.2 Grep the repo for any other doc (`ARCHITECTURE.md`, `SKILL.md`,
      `reference/scripts.md`) that describes the planner returning plan JSON as its final
      message, and update those references to the new status-summary contract. (None
      found -- `ARCHITECTURE.md` and `SKILL.md` already describe the output as
      `BUILD_PLAN.json`, not a JSON reply.)

## 4. Manual verification

- [ ] 4.1 Run a real Phase 2 planning pass (or the closest existing eval case) end to end:
      confirm `BUILD_PLAN.json` lands on disk, `plan_validate.py` output never appears in
      the main session's transcript as raw JSON, and the plan summary checkpoint still
      renders correctly.
- [ ] 4.2 Force a validation error (e.g. temporarily corrupt a required field in the
      planner's draft via a deliberately bad test request) and confirm the planner agent
      retries internally rather than escalating to main on the first error.
