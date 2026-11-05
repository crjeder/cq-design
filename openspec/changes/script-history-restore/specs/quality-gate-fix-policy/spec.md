## ADDED Requirements

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

## MODIFIED Requirements

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
