## Context

`formalize-parameters-sourcing` (archived) shipped `parameters.py` as a pure prose
convention first, then added `_run_parameters_presence_stage` as a *separate,
follow-up* change once the convention had been in use and the gap (nothing checked it
was actually written) was concrete. This change deliberately follows the same
sequencing for `REQUIREMENTS.md`.

## Decision: no gate stage in this change

Ship the write procedure only. Do not add a `requirements_missing` advisory stage to
`src/quality_gate.py` yet.

### Why deferred rather than bundled in

- `REQUIREMENTS.md`'s skip condition is wider and softer than `parameters.py`'s: it
  covers topology ambiguity, fit type, *and* dimension lookups (any one of the three
  triggers the write), versus `parameters.py`'s single trigger (a real-world lookup
  happened). A presence check needs the same three-way disjunction encoded in
  `src/quality_gate.py`, mirrored from prose in a skill doc -- worth doing once the
  actual skip/write split is observed in practice across real requests, not guessed
  from the spec text alone.
- No script or schema currently reads `REQUIREMENTS.md`. Unlike `parameters.py`
  (which at least has the `import_params.py` precedent of being a file scripts touch),
  there's zero code surface yet. Adding a gate check before any other tooling exists
  around the file front-loads maintenance for a check whose false-positive rate is
  unknown.
- Keeping this change docs-only keeps it reviewable and revertable independent of any
  gate/scoring logic.

### Follow-up trigger

Revisit once `REQUIREMENTS.md` has shipped in a handful of real projects: if authors
observe the file being silently skipped when it shouldn't be (the failure mode the
`parameters_missing` stage was built to catch), open a follow-up change adding an
analogous `requirements_missing` advisory stage, gated on
`build/journal.md` containing `phase1/requirements_written` (or the wider trigger
condition, decided at that time) but the file missing/empty.

## Non-Goals

- No change to `BUILD_PLAN.json`'s schema or `plan_validate.py`.
- No new CLI tool for reading, diffing, or validating `REQUIREMENTS.md`.
- No enforcement that Phase 2 planning actually consulted the file -- it is a human
  review artifact, not a machine input, in this change.
