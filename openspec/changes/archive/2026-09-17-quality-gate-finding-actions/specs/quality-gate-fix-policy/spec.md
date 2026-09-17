## ADDED Requirements

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
