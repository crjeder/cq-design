## 1. Schema

- [x] 1.1 Add optional `script_baseline` (object, `additionalProperties: {"type": "string"}`)
  to the `request_log` item schema in `src/build_plan_schema.json`, alongside `level`/`targets`.
- [x] 1.2 Add/extend `tests/test_gate_plan_validation.py` (or wherever `request_log` schema
  cases live) with: an entry carrying `script_baseline` validates; a non-object/non-string-map
  `script_baseline` is rejected.

## 2. Snapshot on append (`log.py`)

- [x] 2.1 In `add_request_log_entry` (`src/log.py`), add a `snapshot_dir: str | None = None`
  parameter. When set and `level == "parameter"`, glob `<snapshot_dir>/*.py`, hash each via
  `freshness.script_hash`, and set `entry["script_baseline"] = {part_id: hash}` (part id =
  filename stem) before schema validation.
- [x] 2.2 Add `--snapshot-scripts <dir>` to the `add` subparser's `argparse` definition and
  thread it through to `add_request_log_entry` in `main`.
- [x] 2.3 `tests/test_log.py`: snapshot recorded for a `parameter`-level add with the flag;
  no `script_baseline` when `--level` is absent or not `parameter`; no `script_baseline`
  when the flag is omitted; hashes match `freshness.script_hash` on the same files.

## 3. Drift check (`quality_gate.py`)

- [x] 3.1 Add a helper that finds the newest `request_log` entry (by `ts`) carrying a
  non-empty `script_baseline`, returning `None` if none exists.
- [x] 3.2 Add a helper that builds the joint-linkage exemption set: for a given set of
  target part ids, every part id appearing alongside one of them in any `joints[].members`
  entry.
- [x] 3.3 Add `_run_parameter_routing_stage(plan, script_path)` (matching the existing
  `_run_hinge_guard_stage`/`_run_gridfinity_stage` shape): resolve the newest baseline entry;
  for each `part_id` in its `script_baseline`, resolve `<script_path's dir>/<part_id>.py`,
  skip if missing, hash it, compare to the baseline; for a mismatch, resolve target part ids
  from the entry's `targets` (bare id or `id.` prefix, matching `render_prompt.scoped_request`'s
  convention); skip if `part_id` is itself a target or in the joint-linkage exemption set;
  otherwise emit one `routing_violation` issue via `units.make_issue` with
  `severity: "warning"`, citing the entry's `text`, the target part(s), and `part_id`.
- [x] 3.4 Wire `_run_parameter_routing_stage` into `run_gate`'s per-part issue collection
  (outside the fix-round loop, once per call — matching the feature-presence/hinge-guard/
  cosmetic-slope/Gridfinity stages' existing placement).
- [x] 3.5 `tests/test_quality_gate.py`: untargeted sibling drift is flagged; targeted part's
  own drift is not flagged; joint-linked sibling drift is not flagged; no baseline present
  produces no findings; a baseline part with no script file on disk is skipped; a
  `routing_violation`-only report still has `passed: true`.

## 4. Orchestrator guidance

- [x] 4.1 In `skill/phase3_build.md`'s correction-handling rule (the `request_log` append
  step), state that a `level: parameter` append SHALL pass `--snapshot-scripts build/`.
- [x] 4.2 In the same section (or wherever `quality_gate.py`'s findings are surfaced to the
  user), note that a `routing_violation` is shown to the user as a warning and does not
  block delivery or consume a fix-round.

## 5. Validation

- [x] 5.1 `openspec validate parameter-entry-routing-check --strict` passes.
- [x] 5.2 `uv run pytest tests/test_log.py tests/test_quality_gate.py tests/test_gate_plan_validation.py`
  passes.
- [x] 5.3 Dry-run against the C5 knuckle-pivot scenario from `TODO.md`: a `parameter` entry
  targeting `cradle` snapshotted before the round, followed by a round that also edits
  `plate.py`'s `PIVOT_Z` with no `joints` entry linking the two, produces a
  `routing_violation` naming `plate`.
- [x] 5.4 Confirm an eval-corpus golden plan (no `request_log`) runs `run_gate` unchanged —
  no baseline, no new findings, no behavior change.
- [x] 5.5 Update `TODO.md`'s "Intent as invariant" residual-gap note to record this item as
  shipped once merged.
