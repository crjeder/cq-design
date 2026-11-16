# Resume: journal contract and interrupted-run recovery

Read this file in full whenever `build/journal.md` already exists in the working
directory at the point `SKILL_DIR` is established — before Phase 0 starts. On a fresh
directory with no journal, skip this file entirely; it costs nothing to a normal run.

## Journal contract

`build/journal.md` is an append-only, human-readable milestone log. It exists so an
interrupted run (usage limit, compaction, crash) can be resumed without re-asking the
user or re-paying for research and part attempts already done. Every phase appends via
`src/log.py journal append <journal_path> <milestone> <text>` rather than hand-composing the
line; the format below is what that command writes.

- **Path:** `build/journal.md` in the caller's working directory. `build/` is created
  at pipeline start (`init_permissions.py`, see SKILL.md Prerequisites), so it exists before
  Phase 0's first possible milestone.
- **Append-only.** One line is appended at the moment a durable fact is established —
  never batched to the end of a phase, never rewritten, reordered, or removed. If a
  later milestone supersedes an earlier one (a part rebuilt after a correction), append
  a new line; leave the earlier one in place.
- **A durable fact** is one that cannot be recomputed from the artifacts already on
  disk: a user decision or approval, a research verdict, an escalation hint, or a
  part's acceptance state. A milestone whose full content already lives in an artifact
  (`BUILD_PLAN.json`, `parameters.py`, a part script, `build/attempts.jsonl`) is
  recorded by pointer, not copied — keep the journal short enough to read back whole in
  one turn.
- **Line format:**
  ```
  - <phase>/<milestone>: <one line stating the fact>
  ```
  `<phase>` is `phase0`..`phase4`. `<milestone>` is a short snake_case key, stable
  across runs so a resumed session can match on it. Timestamps are optional — order of
  appearance is what resume needs; verbatim user wording already has a timestamp in
  `request_log`.

## Milestone table

| Phase | Milestone key | Written when |
|-------|---------------|--------------|
| 0 | `restart` | The user declines to resume and starts over (marks where the new attempt begins) |
| 0 | `sourcing_skipped` | Sourcing triage is skipped (user asked to design from scratch, or the request is custom) |
| 0 | `rung_decision` | The sourcing ladder resolves — text starts `rung <n>`, then source and license verdict. Rung 3 (mesh delivered as-is) skips phases 1-3 |
| 1 | `topology_confirmed` | The user confirms a topology reading at the clarification step |
| 1 | `dimensions_approved` | The user approves/corrects the Phase 1 exit checkpoint — always written, even when nothing was looked up (`parameters.py` is written in the same turn when there are measurements — see `skill/phase1_requirements.md`) |
| 2 | `plan_written` | `BUILD_PLAN.json` passes `plan.py validate` (the script writes the line) |
| 2 | `plan_approved` | The user approves the Phase 2 plan summary |
| 3 | `stub_approved:<part_id>` | The user approves a part's `profile_stub` stage |
| 3 | `part_accepted:<part_id>` | A part passes the Implementation audit (or is accepted as-is at escalation); text ends `sha=<script hash>` (`pipeline.py advance` adds it) |
| 3 | `escalation:<part_id>` | The user resolves a blocked-builder escalation — records the outcome (hint verbatim / accepted as-is / skipped) |
| 3 | `design_approved` | The user approves the Design approval checkpoint (all parts done) |
| 3 | `orientation_chosen` | Print-orientation optimization completes for every union |
| 3 | `assembly_written` | Assembled-pose per-union STLs and the manifest are written (`write_assembly.py` writes the line) |
| 3 | `gate_result` | The quality gate finishes — records pass/fail and remaining error count |
| 4 | `delivered` | Phase 4's model files (`build.py`), report and `README.md` are complete |

## Resume procedure

1. Run `pipeline.py status`, then read `build/journal.md` in full. Only the lines after the last `- phase0/restart:`
   line (or all lines, if there is none) belong to the current attempt; steps 2-4 use
   only those.
2. Cross-check the on-disk artifacts the journal's milestones point to
   (`BUILD_PLAN.json`, `parameters.py`, `build/*.py`, `build/attempts.jsonl`, `stl/`,
   `out/`, `preview/`) — these are authoritative for **content**; the journal is authoritative
   only for **which decisions were already made**. If a part script looks hand-edited
   since its `part_accepted` line (e.g. its `PARAMETERS` block disagrees with
   `BUILD_PLAN.json`'s `dimensions`), treat the script as current per the Design
   approval checkpoint's existing hand-edit rule.
3. Present a short summary: what phase and milestone the journal last recorded, which
   parts (if any) are accepted, and where the run will resume. Ask the user to confirm
   resuming or start over — never resume silently.
4. **Confirmed:** run `pipeline.py status` and continue at `allowed_next[0]` (it applies the
   restart cut and the order rules for you). Name any `void` milestone or `stale_parts` entry
   in the summary: a void line is not trusted, a stale part goes back to its part loop. Do not re-run a phase whose milestone is `done` — e.g.
   `dimensions_approved` present means skip straight past the checkpoint into Phase 2;
   absent with `build/reformulation.md` written but no valid `acceptance.json`, resume at
   the oracle step of the Phase 1 exit checkpoint (spawn a new oracle; the old one is gone);
   `part_accepted:<id>` present for a part means skip its part loop and move to the
   next part. A part that was mid-build has no live builder agent after an interruption:
   spawn a new one; it starts from the script already in `build/<id>.py`.
5. **Declined (start over):** append the restart marker, then restart the pipeline from
   Phase 0. Keep appending to the existing journal rather than truncating it — the old
   lines remain a true record of the prior attempt, and the marker keeps a later resume
   from trusting them.
   ```bash
   uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/log.py" journal append build/journal.md \
       phase0/restart "user started over; earlier milestones void"
   ```

## Updating an existing project

To refresh a project's bundled tooling to the current skill, run `/cq-design:update`.

If no `build/journal.md` exists, none of the above applies — start the pipeline
normally and create the journal on its first milestone.
