## 1. Gate stage

- [x] 1.1 Add `_run_parameters_presence_stage(project_root: str) -> list[dict]` to
      `src/quality_gate.py`, mirroring `_run_telemetry_stage`: read
      `<project_root>/build/journal.md` if present, check for a line starting with
      `- phase1/dimensions_approved`; if found, check `<project_root>/parameters.py`
      exists and is non-empty; emit one `warning`/`parameters_missing` finding via
      `units.make_issue` (`source="parameters"`) when it doesn't, `[]` otherwise.
- [x] 1.2 Wire the stage into `run_gate`: derive `project_root =
      os.path.dirname(os.path.abspath(plan_path))`, call the stage once (outside the
      fix loop, alongside the existing telemetry-presence call), extend `all_issues`.

## 2. Tests

- [x] 2.1 Add `tests/test_quality_gate_parameters.py` covering the four spec scenarios:
      journal+milestone / no file -> warning; journal+milestone / empty file -> warning;
      no journal or no milestone line -> silent regardless of file presence; journal+
      milestone / non-empty file -> silent.
- [x] 2.2 Extend `tests/test_quality_gate.py`'s `run_gate` integration coverage (or add
      a focused test) to confirm the new finding surfaces in the report's `issues` and
      never flips `passed` to `False`.

## 3. Docs

- [x] 3.1 `skill/phase4_deliver.md`: update the existing `parameters.py` pointer line to
      note that a `parameters_missing` gate finding, if present, should be surfaced in
      the delivery summary (same pattern as the existing `telemetry_missing` mention).
- [x] 3.2 Mark the TODO.md item (line ~179, "formalize the `parameters.py`
      sourced-measurements convention") as done, noting the write procedure was already
      prescribed by `add-early-write-journal` and this change closes the remaining
      verification gap; record that extending `import_params.py` was explicitly decided
      against (see design.md Non-Goals).
