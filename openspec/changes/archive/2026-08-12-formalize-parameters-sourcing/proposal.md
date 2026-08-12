## Why

`skill/phase1_requirements.md` and the `dimension-validation-checkpoint` spec already
prescribe writing `parameters.py` (project-root, sourced real-world measurements +
provenance) at the Phase 1 dimension checkpoint, and `skill/phase2_planning.md`
prescribes updating it if planning introduces a new measurement. That half of
TODO.md's "formalize the `parameters.py` sourced-measurements convention" item is
already done. The remaining gap, per the TODO item and confirmed by grep (no
`parameters.py` reference anywhere in `src/`): nothing generates, validates, or
reconciles the file -- it is pure prose convention with no check that it was actually
written when the procedure says it should have been.

## What Changes

- Add an advisory quality-gate stage, `_run_parameters_presence_stage`, mirroring the
  existing `_run_telemetry_stage` pattern in `src/quality_gate.py`: when
  `build/journal.md` records the `phase1/dimensions_approved` milestone (i.e. Phase 1's
  checkpoint ran and sourcing happened) but `parameters.py` is missing or empty at the
  project root, emit a `warning`-severity `parameters_missing` finding. Never blocks the
  gate -- geometry is unaffected either way, same rationale as the telemetry stage.
- Decide and record (not build): extending `import_params.py`'s dimension mapping
  beyond `width`/`depth`/`height` to reconcile `parameters.py` edits is explicitly
  deferred (see design.md) -- the two files hold different kinds of values (raw sourced
  measurements vs. resolved/derived geometry) and no concrete failure has been observed
  from their independence.

## Capabilities

### New Capabilities
- `parameters-provenance-check`: advisory quality-gate stage that warns when
  `parameters.py` is missing after Phase 1's dimension checkpoint recorded that sourcing
  occurred.

### Modified Capabilities
(none -- `dimension-validation-checkpoint` already covers the write procedure; this
change only adds a check that the procedure was followed)

## Impact

- `src/quality_gate.py`: one new advisory stage function + one call site in `run_gate`.
- `skill/phase4_deliver.md`: delivery summary's existing `parameters.py` pointer line
  can now cite the gate finding instead of relying on the author remembering to check.
- No schema change, no new CLI tool, no change to `import_params.py`.
