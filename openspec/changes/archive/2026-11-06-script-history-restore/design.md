## Context

The skill has three kinds of LLM-authored script, all under `build/`:

| Kind | Produced by | Runs through |
|---|---|---|
| Step-form part script (`blocks.Part` steps) | `/cq-design:design` builders | `step_worker.py run`, then `run_cadquery_model.py` as the full tier |
| Legacy part script (raw CadQuery, `PARAMETERS`) | projects from before step form, on resume | `run_cadquery_model.py` |
| Edit script (`build/<stem>_edited.py`) | `/cq-design:edit` | `run_cadquery_model.py` |

`step_worker.py` already logs `run` / `fail` / `restore` events to
`build/<part>.steps.jsonl` and keeps named BRep snapshots (`snapshot save|restore|compare`),
but saving is manual and step-only. The quality gate is report-only; Phase 3 routes
`action: fix` findings to the builder for at most 2 rounds with no comparison between
rounds and no undo. The edit command iterates up to 5 times on `run_cadquery_model.py`
success and a `diff_models.py` check, also with no undo.

The model is a parametric CAD timeline (solidcraft): features with stable ids and a
`suppressed` flag, and whole-document undo snapshots pushed centrally by the command
dispatcher rather than by each command.

## Goals / Non-Goals

**Goals:**
- Every distinct source any of the three script kinds is run with is recoverable, with
  no LLM action.
- Every LLM in the skill (orchestrator, builder, edit command) undoes an edit by
  restoring a stored source, never by hand-reverting text.
- A gate fix round that resolves nothing or regresses is undone before the next round,
  and the delivered part script is never worse at the gate than the accepted one.
- A builder can test "is feature X the cause?" without editing the script.

**Non-Goals:**
- Selective revert of one edit while keeping later ones (a text merge).
- History for `build.py`, the bundled `lib/` tooling, or `BUILD_PLAN.json` (the plan has
  `request_log` and plan revisions).
- Suppression for legacy or edit scripts: they have no plan instance ids.
- A redo stack: the log is append-only, so restoring loses nothing.
- Enforcing edit scope with a step-level diff (possible follow-up).

## Decisions

### 1. One shared module, recorded by the two run tools

`src/script_history.py` owns the store: `build/history/<stem>/<sha12>.py` (first 12 hex of
the source's SHA-256, written once) and `build/history/<stem>/log.jsonl` with `run`,
`mark` and `restore` events. Its function `record_run(script, ok, *, attempt=None,
suppressed=None)` is called by:

- `step_worker.py run`, once per run, with `ok` = every step passed and the full tier
  (when it ran) succeeded, `attempt` = the plan revision it already computes, and the
  `--suppress` ids.
- `run_cadquery_model.py`, once per run, with `ok` = its `success`, and `attempt` when the
  script's directory has a plan containing a part with the script's stem. When the step
  worker runs it as the full tier it sets `CQ_HISTORY_SKIP=1`, so that run is not recorded
  twice.

Alternatives: recording only in `step_worker.py` (misses legacy and edit scripts, the
previous version of this proposal); only in `run_cadquery_model.py` (misses step runs that
fail before the full tier); a `PostToolUse` hook (does not see builder sub-agent tool
calls); `git init` in `build/` (nests a repo in the user's project, needs git on PATH).
The two run tools are the dispatcher equivalent: every script edit is followed by one of
them.

`quality_gate.py` and `build.py` do not record: they run accepted scripts, not edits.

### 2. Restore and mark CLI for every script kind

```
script_history.py restore <target> <script>
script_history.py mark <name> <script>
```

Targets:
- `@last_ok`: `src` of the latest `run` event with `ok: true` and no `suppressed`.
- `@prev`: the latest recorded `src` differing from the current file's hash.
- `@<prefix>`: a unique blob prefix of at least 4 hex characters.
- `<name>`: the `src` of the latest `mark` event with that name. Names may not start
  with `@`.

`mark` stores the current source as a blob if absent and appends a `mark` event. `restore`
rewrites the script, appends a `restore` event (target, resolved hash), and, when
`build/<stem>.steps.jsonl` exists, also appends the step worker's `restore` event there so
`probe_stuck` keeps working. A missing, ambiguous or unknown target returns
`success: false` and leaves the script untouched. Output is one JSON object.

`step_worker.py snapshot save|restore|compare` stays as is for BRep snapshots and
`compare`; the builder prompt points undo at `script_history.py restore`.

### 3. Restore warns across plan revisions

When both the target's latest `run` event and the part's current plan revision are known
and they differ, restore still rewrites the script and returns
`"warning": "attempt_mismatch"` with both values. Part scripts hold no dimensions (step)
or are reconciled through `import-params` (legacy), so an older source against a newer
plan is usually intended. Edit scripts have no plan and never warn.

### 4. Suppress is a step-worker run flag keyed by instance id

`step_worker.py run <script> --suppress <instance_id>` (repeatable) passes the ids to
`Part` through `CQ_SUPPRESS` (JSON list), as `CQ_PRINT_ROTATE` reaches `result()`. For a
suppressed id, `select`, `resize` and `place` record their step with `"suppressed": true`
and return without `_chain`, construction, booleans, `registry.add` or `armed.add`.

- Keyed by instance id, not step index: stable when steps are added; one id covers its
  select/resize/place.
- Skipping `_chain` makes downstream keys equal to the script with those steps deleted,
  so suppress and unsuppress are both cache-warm once each variant has run.
- A run flag, not a `place(..., suppressed=True)` argument, which would be one more text
  edit that can be left in a delivered script.
- Unknown id: `step_plan` error naming the planned ids.

Downstream damage needs no new check: `cut removed no volume`, the solids check, and the
final plan-probe check (`Registry.check(final=True)` checks every plan probe) already
fail a run whose suppressed feature something depends on or the plan requires. A
suppressed run reports `"suppressed": [ids]`, has `full: null`, and is recorded with
`suppressed`, so `@last_ok` skips it. Cold runs never set `CQ_SUPPRESS`.

### 5. The gate reports its own delta

`quality_gate.py --previous <report.json>` adds
`"delta": {"resolved": [...], "regressed": [...]}`. Identity is `(type, union, source)` over
findings whose `action` is `fix` or `re_export`; messages are excluded because they carry
measured numbers. The "did this round help?" comparison is deterministic, so it lives in
the script and the orchestrator reads two lists.

### 6. Who restores what

```
/cq-design:design, Phase 3 (step and legacy part scripts)
  part accepted (audit pass or accept-as-is)
    -> orchestrator: script_history.py mark accepted build/<part>.py
  gate round n (n <= 2), action: fix
    -> builder fixes; re-audit if geometry changed; re-export
    -> gate --previous <round n-1 report>
       resolved empty OR regressed non-empty
         -> orchestrator: script_history.py restore accepted build/<part>.py
         -> next resume: "previous edit reverted: <delta>"
       otherwise -> orchestrator: script_history.py mark accepted (new baseline)
  cap reached, last round reverted -> re-export from accepted, re-run gate, summarize

builder step loop (step scripts)
  an edit breaks a step that passed -> restore @prev (or @last_ok), then a different
  approach; --suppress <id> to test whether a feature is the cause

/cq-design:edit
  a revision turns success: true into false, or fails a diff check the previous
  revision passed -> restore @prev, then revise differently
```

The orchestrator restores in the gate loop because it holds the delta and the round
count; the builder never sees gate reports.

## Risks / Trade-offs

- [Blob growth in `build/history/`] -> one small `.py` per distinct source, never bundled
  or delivered, not pruned.
- [Finding identity too coarse: a second `overhang_exceeded` elsewhere reads as unchanged]
  -> accepted; the round cap still bounds the loop.
- [Two recorders double-log a step script's full tier] -> `CQ_HISTORY_SKIP` on that
  subprocess.
- [Recording fails (read-only dir, disk full)] -> `record_run` failures are swallowed with
  a one-line stderr warning; a run's result must never depend on history.
- [Builder leaves `--suppress` on its last run] -> `full: null` means no valid
  `step_report` for a `passed` contract; audit and gate run the script cold, unsuppressed.
- [New script needs a permission entry] -> add it to `src/skill_permissions.json` with
  the same path forms as `step_worker.py` (forward-slash and backslash forms both, or
  sub-agents get blocked).

## Migration Plan

Additive. Projects without `build/history/` start recording on the next run; restore
before any recorded run reports "no recorded source". Existing named step-worker
snapshots are unaffected. No plan or schema change.

## Open Questions

- Whether the builder should use `--suppress` proactively on `disconnected_body` /
  `cut removed no volume`, or only when stuck.
