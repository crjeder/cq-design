## Why

When a tool script is pointed at a missing, unreadable, or malformed file (a mistyped `--plan` path, a truncated `BUILD_PLAN.json`, an STL that was never exported), several of them die with a raw Python traceback (`FileNotFoundError`, `JSONDecodeError`) instead of a one-line message naming the file and the fix. Claude parses these scripts' output inline during the part loop, so a traceback costs a debugging round trip that a clear message would avoid.

## What Changes

- Add one shared loader in `src/units.py` (`load_plan` already serves every `--plan` CLI) that catches `OSError` / `json.JSONDecodeError` and raises a single `InputFileError` whose message names the file, what was expected (e.g. "BUILD_PLAN.json"), and the cause (missing, is a directory, permission denied, invalid JSON at line/col).
- CLI entry points that call `load_plan` print that message to stderr and exit 1 with no traceback.
- Replace the remaining unguarded `json.load(open(...))` reads of user-supplied paths (`plan.py` `summary`, `quality_gate.py` plan/orientation reads, `model_export.py` orientations, `run_cadquery_model.py` print-orientation read) with the same loader.
- STL loaders (`mesh_io.load_stl`, `measure_stl._load`, `quality_gate`) distinguish "file not found" from "not a valid STL" in their error text.
- Where the script emits the JSON contract (`run_cadquery_model.py`, `quality_gate.py`), a file error becomes a typed `errors` entry (`type: "file_error"`, with `message` and `hint`) rather than a crash. No existing keys change.

## Capabilities

### New Capabilities
- `file-error-reporting`: tool scripts report missing/unreadable/malformed input files as a single actionable message (CLI) or a typed `file_error` entry (JSON contract), never a raw traceback.

### Modified Capabilities
- `structured-errors`: adds `file_error` to the set of typed error categories the wrapper can emit.

## Impact

- Code: `src/units.py`, `src/plan.py`, `src/quality_gate.py`, `src/model_export.py`, `src/run_cadquery_model.py`, `src/mesh_io.py`, `src/measure_stl.py`; CLIs in `build_template.py`, `edge_treatment_check.py`, `feature_presence_check.py`, `kinematic_check.py`, `minimal_cutout_search.py`, `toolpath_speed.py` pick it up through `load_plan`.
- JSON contract: `errors[].type` gains one value; no keys renamed or removed. Exit codes unchanged (1 = failure).
- Tests: new fast tests (no CadQuery) for missing, directory, and malformed-JSON inputs.
- No new dependencies.
