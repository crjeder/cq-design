## Context

Six of the skill's ~31 CLI scripts split into two shape-alike clusters: three
append-or-search one file under `build/` (`journal.py`, `telemetry.py`,
`request_log_search.py`), three read/validate/write `BUILD_PLAN.json`
(`plan_validate.py`, `plan_summary.py`, `import_params.py`). Two of the six
(`plan_validate.py`, `telemetry.py`'s `fold_attempts`) are also imported
in-process by `quality_gate.py` and `render_prompt.py`, not just invoked as
subprocesses -- the merge has to preserve both call paths.

`render_prompt.py` already dispatches five prompt kinds (`builder`, `audit`,
`planning`, `research`, `sourcing`) through one `argparse` subparser tree; this
change applies the same pattern to the two clusters.

## Goals / Non-Goals

**Goals:**
- One CLI entry point per cluster (`log.py`, `plan.py`), each script's existing
  subcommand names preserved one level deeper (e.g. `telemetry.py append` ->
  `log.py attempt append`) so the merge is a dispatch-tree change, not a
  flag redesign.
- Every in-process import (`quality_gate.py` -> `plan_validate.py`'s validator,
  `render_prompt.py` -> `telemetry.py`'s `fold_attempts`) repoints to the new
  module with no behavior change.
- `skill_permissions.json`, `reference/scripts.md`, and every phase doc's example
  invocation updated in the same change so nothing is left calling a deleted script.

**Non-Goals:**
- No change to any validation rule, journal line format, `attempts.jsonl` record
  shape, or `request_log` entry shape.
- No change to `BUILD_PLAN.json` schema.
- Not merging any other script cluster (e.g. the `*_check.py` geometry gates
  already share one caller, `quality_gate.py`, and gain nothing from a CLI merge --
  see the explore-mode discussion this change followed from).
- Not restructuring `reference/scripts.md` into per-phase files (a separate,
  larger idea the same discussion raised and explicitly deferred).

## Decisions

**One dispatcher module per cluster, not a single `tools.py` for both.**
The two clusters don't share callers or data (`build/*.jsonl`/`.md` vs.
`BUILD_PLAN.json`); a single combined script would need a third dispatch level
for no shared benefit. Two files matches the two shapes.

**Two-level subcommands (`log.py attempt audit-fail`, not `log.py
audit-fail`).** `telemetry.py` alone already has two subcommands
(`append`, `audit-fail`); folding three scripts' subcommands into one flat
namespace on `log.py` risks collisions and hides which original script owns
which behavior. `log.py {journal,attempt,request} <verb> ...` and `plan.py
{validate,summary,import-params}` (the last three don't collide, so `plan.py`
stays one level) keep each cluster's origin legible.

**Move code, don't wrap.** `append_line`, `fold_attempts`,
`append_attempt_record`, the plan validator functions, etc. move into
`log.py`/`plan.py` bodily (same function signatures) rather than staying in
the old files with `log.py` importing them as thin CLI shims. A thin-shim
approach would keep six files alive as libraries while only merging the CLI
surface, defeating the doc/permission-count goal from the proposal.

**Permissions: replace, don't add.** `skill_permissions.json`'s six
Bash/PowerShell pattern pairs for the replaced scripts are removed and two new
pairs (`log.py *`, `plan.py *`) added, rather than keeping the old patterns
around for compatibility -- the old scripts no longer exist, so a stale
allow-pattern is dead weight, not a safety net.

**Spec updates are text-only where the reference is a literal invocation.**
Per the proposal's Impact section, ~15 specs name `plan_validate.py` (or one of
the other five) as the owner of a rule, not as a description of its CLI shape.
Those get the invocation string swapped (`plan_validate.py BUILD_PLAN.json` ->
`plan.py validate BUILD_PLAN.json`) with no requirement wording change. Only
`build-journal`, `attempt-telemetry`, `request-log-search`,
`gate-plan-validation`, `plan-summary-checkpoint`, and `parameter-round-trip`
own requirements that describe the CLI contract itself and need a substantive
delta spec.

## Risks / Trade-offs

[Wide mechanical edit surface -- ~15 spec files, `reference/scripts.md`,
`skill/*.md`, `prompts/*.md`, `SKILL.md`, `skill_permissions.json`, tests] ->
Mitigation: every edit in that set is a literal string substitution
(`old_script.py <subcommand-if-any>` -> `new.py <cluster-subcommand>`), doable
mechanically per-file and checkable by grepping for the six old filenames
returning zero hits outside `openspec/changes/*/`(archived changes keep their
historical text).

[`quality_gate.py` and `render_prompt.py` import the moved code; a missed
import site fails at gate/prompt-render time, not at merge time] -> Mitigation:
`grep -rn "from plan_validate\|from telemetry\|import plan_validate\|import
telemetry" src/` before and after the move to confirm both call sites are
updated; existing `test_run_evals.py`/`test_quality_gate.py`/
`test_render_prompt.py` exercise both in-process paths already.

[A stale doc or prompt still tells Claude to invoke a deleted script mid-pipeline,
producing a `FileNotFoundError` the gate has no typed error for] -> Mitigation:
grep for each of the six old filenames across `SKILL.md`, `skill/`, `prompts/`,
`reference/` as a tasks.md checklist item, not just the code.

## Migration Plan

No runtime migration -- this only touches the skill's own source and docs, not
a running pipeline's persisted state (`journal.md`, `attempts.jsonl`,
`BUILD_PLAN.json` formats are unchanged). Order: move code into the two new
modules -> repoint the two in-process imports -> update
`skill_permissions.json` -> update docs/prompts -> update tests -> delete the
six old files -> update the ~15 spec files' literal invocations -> run the
full test suite and `evals/run_evals.py` (score-only) as a final check that no
call site was missed.

Rollback: revert the commit; nothing external depends on `log.py`/`plan.py`
existing yet since this is a same-PR introduction.

## Open Questions

None -- the invocation shapes, call sites, and spec blast radius are enumerated
above from reading the actual code and specs, not assumed.
