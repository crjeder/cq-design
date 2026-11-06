# quality-gate-fix-policy

## Purpose

Defines the default behavior of `quality_gate.py` with respect to modifying
part scripts: report-only by default, with fixing an explicit opt-in, and how
findings route into the caller's own fix path versus the standalone
cold-context fixer.

## Requirements

### Requirement: The quality gate is report-only by default

`quality_gate.py` SHALL NOT modify the part script unless the caller explicitly
requests it. `run_gate`'s `allow_fix` parameter SHALL default to `False`, and the
CLI SHALL expose an opt-in `--fix` flag rather than an opt-out `--no-fix` flag. A
run without `--fix` SHALL execute every check stage and emit the same report
structure (`passed`, `issues`, `print_recipe`, `fix_rounds`) and the same exit
code as before, with `fix_rounds` at 0.

#### Scenario: Default run reports without rewriting

- **WHEN** `quality_gate.py --script <part>.py --plan BUILD_PLAN.json` runs and a
  check emits a `severity: error` finding
- **THEN** the report lists the finding, the process exits non-zero, and the part
  script on disk is byte-identical to what it was before the run

#### Scenario: Explicit opt-in restores the fixer

- **WHEN** the same command is run with `--fix`
- **THEN** the cold-context fixer runs for at most `MAX_FIX_ROUNDS` rounds exactly
  as it did before this change, and `fix_rounds` reports how many ran

#### Scenario: Stale caller fails loudly

- **WHEN** a caller passes the removed `--no-fix` flag
- **THEN** the CLI exits with an unrecognized-argument error rather than silently
  accepting it

### Requirement: Every finding carries an action

`run_gate` SHALL set an `action` key, one of `fix`, `re_export`, `ask_user`, or
`warn_only`, on every finding in `issues` before returning the report, computed from
that finding's `type` and `severity` alone -- no check-module call site (`make_issue`
or a raw dict literal) SHALL be required to pass `action` itself. The default SHALL be
`severity: error` -> `fix`, `severity: warning` -> `warn_only`, `severity: info` ->
`warn_only`, overridden by `type` for exactly: `stale_artifact` -> `re_export`;
`motion_collision`, `range_exceeds_limit` -> `ask_user`; `contact_limited_stop` ->
`ask_user`. Every other finding type existing at the time of this change (the DFM
wrapper types, `non_watertight`, `invalid_geometry`, `mesh_load_error`,
`overhang_exceeded`, `plan_invalid`, `keep_out_violation`, `plate_clearance`,
`feature_absent`, `feature_drift`, `hinge_guard_missing`, `cosmetic_slope`,
`check_skipped`, `range_check_not_applicable`, `telemetry_missing`,
`parameters_missing`, `parameters_unresolved`, every `gridfinity_*` type) SHALL take
the severity default with no override.

#### Scenario: Error finding defaults to fix

- **WHEN** the gate emits a `severity: error` finding whose `type` has no override
  (e.g. `non_watertight`, `keep_out_violation`, `gridfinity_footprint`)
- **THEN** its `action` is `fix`

#### Scenario: Warning finding defaults to warn_only

- **WHEN** the gate emits a `severity: warning` or `severity: info` finding whose
  `type` has no override (e.g. `edge_treatment`, `cosmetic_slope`, `overhang_exceeded`
  at a declared clearance opening)
- **THEN** its `action` is `warn_only`

#### Scenario: Stale artifact routes to re-export, not a builder fix

- **WHEN** the gate emits a `stale_artifact` finding (from the kinematic, plate-
  clearance, or keep-out stage)
- **THEN** its `action` is `re_export` regardless of its `severity`

#### Scenario: Ambiguous-remedy and judgment-call findings route to ask_user

- **WHEN** the gate emits a `motion_collision`, `range_exceeds_limit`, or
  `contact_limited_stop` finding
- **THEN** its `action` is `ask_user` regardless of its `severity`

### Requirement: Gate findings route into the caller's fix path

Phase 3 SHALL run the gate without `--fix` and SHALL route each finding by its
`action` field rather than by inspecting `type` or `severity` itself:
- `fix` -> apply a targeted fix to the offending part's script using the finding's
  `type`, `message`, and `hint`, re-audit if geometry changed, then re-run Model export
  and the gate.
- `re_export` -> re-run Model export and the gate; no part script is touched.
- `ask_user` -> surface the finding's `message` and `hint` and ask before taking any
  action; do not resume a builder or re-export on the pipeline's own initiative.
- `warn_only` -> surface the finding alongside the print recipe; never triggers a fix
  round.

`fix`- and `re_export`-driven rounds SHALL be bounded at 2 per part, after which the
remaining findings are escalated to the user rather than retried. `skill/phase3_build.md`
SHALL express this routing generically by `action` and SHALL NOT enumerate individual
finding `type`s.

For every part script (step-form or legacy), the orchestrator SHALL run
`script_history.py mark accepted build/<part_id>.py` when the part is accepted (audit
pass or accept-as-is). Every gate re-run after a `fix` round SHALL pass `--previous` with
the prior round's report. When `delta.resolved` is empty or `delta.regressed` is
non-empty, the orchestrator SHALL run `script_history.py restore accepted
build/<part_id>.py` before anything else, and the next round's builder resume SHALL state
that the previous edit was reverted and why. Otherwise it SHALL mark `accepted` again as
the new baseline. When the round cap is reached and the last round was reverted, Model
export and the gate SHALL be re-run from the restored script before the remaining
findings are summarized, so delivered files come from `accepted`.

#### Scenario: Gate error is fixed with full context

- **WHEN** the gate reports a finding with `action: fix`
- **THEN** the part's script is corrected in the part loop from the finding's typed
  message and hint, and the gate is re-run against the corrected script

#### Scenario: Stale artifact is re-exported, not sent through the builder

- **WHEN** the gate reports a finding with `action: re_export`
- **THEN** Model export and the gate are re-run without resuming any part's builder

#### Scenario: Ambiguous-remedy finding is escalated, not auto-fixed

- **WHEN** the gate reports a finding with `action: ask_user`
- **THEN** the finding's `message` and `hint` are surfaced to the user and no fix,
  re-export, or builder resume happens until the user responds

#### Scenario: Gate fix rounds are bounded

- **WHEN** two `fix`/`re_export`-driven gate rounds have run for a part and a
  non-`warn_only` finding remains
- **THEN** no further gate-fix round is attempted and the remaining findings are
  summarized to the user

#### Scenario: Warn-only findings do not trigger a fix round

- **WHEN** the gate reports only `action: warn_only` findings
- **THEN** the gate passes, no fix round runs, and the findings are surfaced alongside
  the print recipe

#### Scenario: A regressing fix round is undone

- **WHEN** gate round 1's fix leaves `delta.regressed` non-empty
- **THEN** the orchestrator restores `accepted`, and the round-2 resume tells the builder
  its previous edit was reverted together with the regressed findings

#### Scenario: A round with progress becomes the baseline

- **WHEN** gate round 1's fix resolves a finding and regresses none
- **THEN** the edited script is kept and marked as `accepted`

#### Scenario: Delivery after an exhausted, reverted loop

- **WHEN** round 2 is reverted and findings remain
- **THEN** export and the gate re-run from `accepted` before the summary, and the
  delivered files are built from `accepted`

### Requirement: The cold-context fixer remains available

The `--fix` path SHALL keep the existing fix-prompt renderer and `claude -p`
invocation, so the gate remains usable standalone outside the skill pipeline.
Removing the default SHALL NOT remove the capability. The `claude -p` invocation SHALL
select its model from `skill_config.json`'s `models.fix_loop`, appending
`--model <value>`; a value of `"inline"`, a missing key, or a missing config file
SHALL invoke `claude -p` with no `--model` flag.

#### Scenario: Standalone scripted use

- **WHEN** the gate is invoked outside the skill with `--fix` on a script with a
  fixable error
- **THEN** it renders the targeted fix prompt, invokes the model, writes the
  corrected script, and re-runs the checks

#### Scenario: Configured fix-loop model

- **WHEN** `skill_config.json` sets `models.fix_loop` to a model id and the gate runs
  with `--fix`
- **THEN** the `claude -p` invocation carries `--model <that id>`

#### Scenario: Unconfigured fix loop is unchanged

- **WHEN** the gate runs with `--fix` and no `skill_config.json` exists in the working
  directory
- **THEN** `claude -p` is invoked with no `--model` flag and the fix path behaves
  exactly as before this change

### Requirement: The gate reports a delta against a previous report
`quality_gate.py --previous <report.json>` SHALL add
`"delta": {"resolved": [...], "regressed": [...]}` to its report. A finding's identity
SHALL be its `(type, union, source)`, taken over findings whose `action` is `fix` or
`re_export`. `resolved` SHALL list identities present in the previous report and absent
from this one; `regressed` SHALL list identities present in this report and absent from
the previous one. Without `--previous` the report SHALL carry no `delta` key. An
unreadable or non-JSON previous report SHALL exit 1 with an error naming the path, never
an empty delta.

#### Scenario: A round that fixed one finding
- **WHEN** the previous report had `non_watertight` and `overhang_exceeded` and this run
  has only `overhang_exceeded`
- **THEN** `delta.resolved` lists `non_watertight` and `delta.regressed` is empty

#### Scenario: A round that introduced a new error
- **WHEN** this run has a `keep_out_violation` the previous report did not
- **THEN** `delta.regressed` lists `keep_out_violation`
