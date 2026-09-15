## Why

`build/attempts.jsonl` is the measurement baseline every prompt, reference, and
model-routing change is judged against, but a real 7-round session (the C5
Phone-Holder project) finished with no telemetry file at all. The Step 5 append
is prescribed in `skill/phase3_build.md` yet nothing verifies it happened, so a
skipped append is silent: the eval harness's first-shot-rate / attempts-to-pass /
cost metrics have no data from exactly the sessions they exist to measure.

## What Changes

- The quality gate gains a telemetry-presence stage: when `build/attempts.jsonl`
  is missing, empty, or contains no parseable record, the gate emits a `warning`
  finding (`source: "telemetry"`, `type: "telemetry_missing"`). Warning only --
  a missing log never blocks delivery.
- The gate resolves the log path relative to the part scripts' directory (the
  `build/` directory the loop writes to), with an explicit CLI override.
- Phase 4 delivery reports the finding to the user rather than silently dropping it.

No change to `src/telemetry.py`, the record schema, or the Step 5 prescription
itself -- verification confirmed Step 5 already prescribes the append per attempt
and per correction round.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `attempt-telemetry`: adds a requirement that the absence of the log is detected
  and surfaced at delivery, instead of the log being write-only-by-convention.

## Impact

- `src/quality_gate.py`: one new stage function + call site in `run_gate`, one new
  CLI flag (`--attempts-log`).
- `skill/phase4_deliver.md`: report the warning in the delivery status.
- `tests/test_quality_gate_telemetry.py` (new, fast, no CadQuery): missing /
  empty / populated log cases.
- No effect on `src/telemetry.py`, the JSONL format, or existing logs.
