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

### Requirement: Gate findings route into the caller's fix path

Phase 3 SHALL run the gate without `--fix` and SHALL handle its findings in the
part loop's own fix path, where the plan entry, the rendered views, and the
attempt history are already in context. On any `severity: error` finding the
orchestrating session SHALL apply a targeted fix to the offending part's script
using the finding's `type`, `message`, and `hint`, then re-run the gate. Gate-
driven fix rounds SHALL be bounded at 2 per part, after which the remaining
findings are escalated to the user rather than retried.

#### Scenario: Gate error is fixed with full context

- **WHEN** the gate reports an error for a part
- **THEN** the part's script is corrected in the part loop from the finding's
  typed message and hint, and the gate is re-run against the corrected script

#### Scenario: Gate fix rounds are bounded

- **WHEN** two gate-fix rounds have run for a part and an error remains
- **THEN** no further gate-fix round is attempted and the remaining findings are
  summarized to the user

#### Scenario: Warnings do not trigger a fix round

- **WHEN** the gate reports only `severity: warning` findings
- **THEN** the gate passes, no fix round runs, and the warnings are surfaced
  alongside the print recipe

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
