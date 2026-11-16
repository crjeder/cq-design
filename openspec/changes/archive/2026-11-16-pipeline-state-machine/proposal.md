## Why

The pipeline order exists only as prose in `SKILL.md` and `skill/phase*.md`. Claude drives it inline, so the recurring defects are process drift, not geometry: sub-agents re-plan into downstream steps, resume trusts stale milestones (PR #250), and an edit run skipped the pipeline. A small program that owns the build state and refuses invalid steps turns sequencing, resume and sub-agent scope from instructed into checkable (decision A in `documentation/pipeline.md`; TODO section 1).

## What Changes

- Add `src/pipeline.py` (stdlib only, no CadQuery): reads the build state and reports the route, completed steps, allowed next steps and, for each blocked step, the unmet precondition.
- Build state is **derived, not stored**: journal milestones (decisions) plus artifact existence and script hashes (content). No second state file that can drift.
- A milestone is valid only if it comes after the latest line of every prerequisite milestone. Re-approving the dimensions after the plan was approved therefore voids the plan approval and everything downstream, modelling the "loops back" table without timestamps.
- `pipeline.py advance <milestone> <text>` validates the transition, then appends the journal line (through `log.append_line`); a transition whose preconditions are unmet exits non-zero with a typed error and writes nothing. It is the path for user-decision milestones; `status` also voids any line written another way whose prerequisites are unmet.
- Routes `design`, `plan` and `edit` are explicit. `edit` is a plan-less route: no `BUILD_PLAN.json` and no `build/` is the normal state, not an error, and the gated steps (`print_orientation`, `quality_gate`) are refused on it.
- `part_accepted:<id>` records the part script's hash, so an accepted part whose script changed since is reported stale and returns to the part loop.
- `skill/resume.md`, `SKILL.md` and the builder prompt read `pipeline.py status` instead of re-deriving the next step from prose; the builder prompt names the steps its part may run.
- Out of scope: steps 11-14 of `documentation/pipeline.md` (slicing, G-code checks), hooks gating individual tool calls (hooks do not see sub-agent calls), and the telemetry hook reading the state (follow-up).

## Capabilities

### New Capabilities
- `pipeline-state-machine`: derived build state, route model including the plan-less edit route, transition preconditions, invalidation by later upstream milestones, part staleness, and the `status` / `can` / `advance` CLI contract.

### Modified Capabilities
- `build-journal`: the resume procedure reads `pipeline.py status` for the resume point (and ignores milestone lines whose prerequisites are unmet) rather than inferring it from the journal by hand. Script-written milestones (`plan_written`, `assembly_written`) keep appending themselves.

## Impact

- New: `src/pipeline.py`, `tests/test_pipeline.py`, contract entry in `reference/scripts.md`, line in `FILES.md`.
- Changed: `skill/resume.md`, `SKILL.md`, `skill/phase*.md` milestone-append calls, `src/render_prompt.py` (builder prompt gains an allowed-steps line), `src/log.py` (no behaviour change; `append_line` reused).
- No change to the JSON contracts of `run_cadquery_model.py` or `quality_gate.py`; existing journals stay readable (lines without a part hash are treated as unknown, not stale).
- Doc: `TODO.md` section 1 item and `documentation/todo-pipeline.md` closed on completion.
