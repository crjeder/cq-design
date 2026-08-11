## Why

IMPROVEMENT_PLAN item 9. `run_cadquery_model.py` already maintains `_OCC_HINTS`,
a translation table from six known OCC exception classes (`Standard_ConstructionError`,
`BRep_API`, `StdFail_NotDone`, `Standard_NullObject`, `Standard_OutOfRange`,
`Standard_TypeMismatch`) to specific, actionable hint text. But every one of them
still reports `"type": "occ_exception"` with the class name buried in an `occ_class`
field — the fix loop, telemetry (`build/attempts.jsonl`), and `quality_gate.py`'s
severity table all see one undifferentiated bucket, the same problem the
`silent_boolean`/`feature_overflow`/`workplane_drift` family already solved for
runtime verify-helper failures. `occ_exception` is the least targeted retry
because it's the least specific error.

No telemetry data exists in this repo to rank signatures by frequency (`build/`
is per-working-directory and gitignored), so this proposal does not invent new
detections — it operationalizes the six-class table that already exists and is
already cited by `occ-error.md`'s worked-around signatures (item 6) and the
Tier 1 anti-patterns doc.

## What Changes

- Each of the six known `_OCC_HINTS` classes gets its own `type` value instead
  of the shared `occ_exception` fallback:

  | OCC class | new `type` |
  |---|---|
  | `Standard_ConstructionError` | `construction_error` |
  | `BRep_API` | `command_not_done` |
  | `StdFail_NotDone` | `fillet_failure` |
  | `Standard_NullObject` | `null_object` |
  | `Standard_OutOfRange` | `index_out_of_range` |
  | `Standard_TypeMismatch` | `type_mismatch` |

  The `occ_class` field and hint text are unchanged — only what `type` carries.
- An OCC exception class **not** in the table still falls back to
  `type: "occ_exception"` with the generic hint, unchanged from today. This
  fallback is the thing that stays "least targeted" — by design, since no new
  signature is being added, only the six already-known ones are split out.
- `quality_gate.py`'s severity table (`_run_wrapper`, the tuple currently
  containing `"occ_exception"`) is updated to list all six new types plus the
  `occ_exception` fallback as `severity: error` — otherwise the split silently
  demotes every known OCC failure to a warning.
- `skill/phase3_build.md`'s blocking-error-types line gets the same six types
  added alongside `occ_exception`.
- `SKILL.md`'s error-type table row for `occ_exception` is split into six rows
  (one per new type, hint summary) plus one row for the unmapped fallback.

## Capabilities

### Modified Capabilities
- `structured-errors`: known OCC exception classes map to a distinct `type`
  each, not a shared `occ_exception` type differentiated only by `occ_class`.

## Impact

- `src/run_cadquery_model.py`: `_OCC_HINTS` becomes `{class: (type, hint)}`,
  `_translate_stderr`'s emit block.
- `src/quality_gate.py`: severity-table tuple (~line 88).
- `skill/phase3_build.md`: blocking error types line (~line 327).
- `SKILL.md`: error-type table (~line 222).
- `tests/test_run_wrapper.py`: existing OCC-exception assertions
  (`occ[0]["occ_class"] == "StdFail_NotDone"`) gain a `type` assertion; add one
  case per new type plus one for an unmapped class staying `occ_exception`.
- `tests/test_run_evals.py`: `error_types` fixture value is unaffected (uses a
  synthetic list, not the real translation table).
- `IMPROVEMENT_PLAN.md` item 9 status.
