## 1. Provenance stamp primitive

- [x] 1.1 Create `src/freshness.py`: `script_hash(script_path) -> str` (SHA-256 hex digest
      of file bytes), `is_stale(stamped_hash: str | None, script_path: str) -> bool`
      (`None` -> `False`), `MANIFEST_FILENAME`, `write_manifest(stl_dir, union_scripts,
      keep_out_scripts) -> str`, `read_manifest(stl_dir) -> dict | None`. Stdlib only
      (`hashlib`, `json`, `os`, `datetime`).
- [x] 1.2 Create `tests/test_freshness.py`: hash determinism and sensitivity to any content
      change, `is_stale` truth table (matching/mismatching/absent stamp), manifest
      round-trip (write then read), `read_manifest` returns `None` when the file is absent.

## 2. Stamp at write time — orientation result

- [x] 2.1 Add optional `--source-script` argument to `src/print_orientation.py`'s CLI; when
      given, stamp the result dict with `source_script_hash` (via `freshness.script_hash`)
      before printing. Omitted stays unstamped.
- [x] 2.2 In `src/build_template.py`, stamp every freshly computed orientation (`_orientation_for`
      result) with the current script's hash before storing it in `summary`/`orientations`,
      so a recomputed entry is self-describing for the next run.
- [x] 2.3 Update `tests/test_print_orientation.py` (or add cases) covering `--source-script`
      stamping the CLI JSON output, and its absence leaving the result unstamped.

## 3. Stamp at write time — export manifest

- [x] 3.1 In `src/model_export.py`'s `export_model`, after writing the per-union and
      keep-out-zone STLs, call `freshness.write_manifest(stl_dir, union_scripts,
      keep_out_scripts)` with `{uid: (part_id, script_path)}` / `{"<part_id>::<zone>":
      (part_id, script_path)}` built from the existing per-part loop, and include the
      manifest path in the returned result dict.
- [x] 3.2 Extend `tests/test_model_export.py` (the actual `export_model` test file, not
      `test_exporters.py`) asserting `export_manifest.json` is written with one entry per
      exported union and per exported keep-out zone, each carrying the correct script's
      hash.

## 4. Verify at read time — build.py orientation reuse

- [x] 4.1 In `src/build_template.py`'s `resolve_orientations`, before reusing an accepted
      entry, compare its `source_script_hash` (if any) against the current script via
      `freshness.is_stale`; on staleness, fall through to the existing recompute path and
      stamp the new result, and record the union id in a "recomputed" list returned
      alongside `orientations`/`summary`.
- [x] 4.2 Update `_print_summary` (and `main`) to print a note listing which unions were
      recomputed due to a stale accepted orientation and why.
- [x] 4.3 Extend `tests/test_build_script.py`: an accepted entry with a matching stamp is
      reused; a mismatching stamp is recomputed and the result is stamped; an entry with no
      stamp is reused unconditionally (unchanged prior behavior).

## 5. Verify at read time — whole-model check stages

- [x] 5.1 Add an optional `parts_dir: str | None = None` parameter (and `--parts-dir` CLI
      flag via `units.py`'s shared argument helpers) to `run_kinematic_check`,
      `run_plate_clearance_check`, `run_keep_out_check`.
- [x] 5.2 In each stage, when `parts_dir` is given: read the export manifest
      (`freshness.read_manifest(stl_dir)`); when present, for each union (kinematic: subtree
      + fixed ids; plate-clearance: every co-plated union; keep-out: the zone's declaring
      part and every foreign union checked against it) resolve its owning part id via
      `iter_unions`/the zone's declaring part, compare the manifest's stamp against
      `<parts_dir>/<part_id>.py` via `freshness.is_stale`, and on staleness append a
      `stale_artifact` `error` finding (shared `{source, severity, type, message, hint}`
      contract) naming the union/zone, excluding it from that check's geometry comparison
      (mirroring the existing missing-STL `continue`).
- [x] 5.3 When `parts_dir` is `None` or the manifest is absent, emit one `check_skipped`
      `warning` for the freshness check (distinct message from the missing-STL skip) and
      continue running the stage's other checks unaffected. (Kinematic stage additionally
      suppresses this warning when the collision backend itself is already unavailable, to
      avoid a redundant second `check_skipped` when the sweep won't run at all.)
- [x] 5.4 Extend `tests/test_kinematic_check.py`, `tests/test_plate_clearance_check.py`,
      `tests/test_keep_out_check.py`: fresh manifest passes through unaffected; stale
      manifest entry yields `stale_artifact` and excludes that union from the
      collision/clearance result; absent manifest or `parts_dir` degrades to
      `check_skipped` without blocking the rest of the stage.

## 6. Wire into the quality gate

- [x] 6.1 In `src/quality_gate.py`, derive `parts_dir` from
      `os.path.dirname(os.path.abspath(script_path))` (the same directory `stl_dir` already
      defaults from) and pass it through `_run_kinematic_stage`, `_run_plate_clearance_stage`,
      `_run_keep_out_stage` to the corresponding `run_*_check` calls.
- [x] 6.2 Confirmed `stale_artifact` findings surface in the aggregated report and count
      toward pass/fail via the existing severity-generic aggregation (no special-casing
      needed).
- [x] 6.3 Added `tests/test_gate_freshness.py`: a stale co-plated union's exported STL
      surfaces as `stale_artifact` end-to-end through `run_gate`, fails the gate, and is
      excluded from the plate-clearance comparison.

## 7. Documentation

- [x] 7.1 Updated `skill/phase3_build.md`: added an "Artifact freshness" section documenting
      what `stale_artifact` means and the re-export remedy; the `--source-script` flag in
      the `print_orientation.py` invocation example; `freshness.py` added to the `lib/`
      bundle list (prose, both shell snippets, and the directory-layout diagram).
- [x] 7.2 Updated `CLAUDE.md`'s Core Scripts table: added a `src/freshness.py` row; amended
      the `model_export.py`, `build_template.py`, `kinematic_check.py`,
      `plate_clearance_check.py`, `keep_out_check.py` rows for the new freshness behavior;
      added `freshness.py` and `test_freshness.py` to the File Layout listing.
- [x] 7.3 Marked the "orientation cache staleness" sub-item done in `TODO.md`, noting the
      fix.

## 8. Full verification

- [x] 8.1 Ran `uv run pytest tests/`: 620 passed, 0 failed. Also confirmed lint (`ruff
      check`), formatting (`ruff format --check`), `mypy`, and `basedpyright` are clean on
      every file touched by this change.
- [x] 8.2 The phone-holder scenario (a script edit that changes geometry without changing
      the bbox, so a stale cache silently regenerates against superseded geometry) is
      covered end-to-end by automated tests rather than a manual scratch-project repro:
      `tests/test_build_script.py::test_build_py_recomputes_stale_orientation` (a stamped
      `orientations.json` entry that no longer matches its script is recomputed, not
      reused, and the recompute is reported) and
      `tests/test_gate_freshness.py::test_stale_export_surfaces_through_gate` (a stale
      exported STL surfaces as a blocking `stale_artifact` finding through the full gate,
      excluded from the geometry comparison, rather than passing on superseded geometry).
