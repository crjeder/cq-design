## Why

Every LLM-authored script in the skill (step-form part scripts from `/cq-design:design`,
legacy part scripts on resume, and `/cq-design:edit` scripts) is undone by hand-editing
the text back, which can clobber code the edit never touched. The only recorded history
is a named step-worker snapshot the builder has to remember to save, and it exists only
for step scripts. When a quality-gate fix round or an edit-command revision makes a script
worse, the next attempt stacks another edit on the failed one, and after the round cap the
delivered part script may be an unaudited, gate-worse version of the one that was accepted.

## What Changes

- New `src/script_history.py`: a content-addressed source log per script in
  `build/history/<stem>/`. Both tools every script runs through record into it:
  `step_worker.py run` (each step run) and `run_cadquery_model.py` (every other run).
  No LLM action is needed for history to exist.
- `script_history.py restore <target> <script>` works for every script kind. Targets:
  `@last_ok` (latest successful, unsuppressed run), `@prev` (the distinct source run before
  the current one), `@<hash prefix>`, or a mark name. `script_history.py mark <name>
  <script>` records a named baseline. A restore across plan revisions warns.
- `step_worker.py run --suppress <instance_id>` (repeatable, step scripts only) skips every
  step of that plan instance without editing the script, keeping the cache warm. A
  suppressed run never runs the full tier and never counts as `@last_ok`.
- `quality_gate.py --previous <report>` adds a `delta` block (`resolved`, `regressed`
  finding identities) against the previous round's report.
- Orchestrator instructions (`skill/phase3_build.md`): mark `accepted` at each part's
  acceptance; in the gate fix loop, restore `accepted` when a round resolves nothing or
  regresses, re-mark it on progress, and after the round cap re-export from `accepted`.
  Applies to step and legacy part scripts alike.
- Builder instructions (`prompts/builder.md`): undo with `script_history.py restore`,
  never by hand-reverting; use `--suppress` to test whether one feature causes a failure.
- Edit command (`commands/edit.md`): when a revision turns a passing run or diff check
  into a failing one, restore `@prev` before revising again instead of stacking edits.

## Capabilities

### New Capabilities
- `script-history`: per-script source log recorded by the run tools, restore and mark
  targets for any script kind, and run-time step suppression for step scripts.

### Modified Capabilities
- `step-worker`: `run` records each run into script history (with `--suppress` state).
- `quality-gate-fix-policy`: gate reports a `delta` against a previous report; the gate
  fix loop marks and restores `accepted` for every part script.
- `step-edit-command`: the validate-and-diff iteration restores `@prev` after a
  regressing revision.

## Impact

- New `src/script_history.py`; `src/step_worker.py` (recording, `--suppress` plumbing),
  `src/run_cadquery_model.py` (recording), `src/blocks/part.py` (suppressed steps),
  `src/quality_gate.py` (`--previous`, `delta`).
- `skill/phase3_build.md`, `prompts/builder.md`, `commands/edit.md`, `reference/scripts.md`,
  `FILES.md`, and the permission allow-list (`src/skill_permissions.json`) for the new script.
- Tests: new `tests/test_script_history.py`; `tests/test_step_worker.py`,
  `tests/test_step_part.py`, `tests/test_quality_gate.py`.
- `build/history/` grows by one small `.py` blob per distinct source; it is never bundled
  into `lib/` or a deliverable. `build.py` and the bundled `lib/` tooling do not record.
