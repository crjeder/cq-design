## Context

`units.load_plan` is the shared `--plan` loader for six CLIs and does a bare `open` + `json.load`. `plan.py`, `printer_profile_validate.py` and `regen_prompt.py` already catch `OSError`/`JSONDecodeError` locally, each with its own wording. `quality_gate.py`, `model_export.py` and `run_cadquery_model.py` read plan/orientation/config JSON with no guard. STL loaders already wrap trimesh failures in `ValueError` but lump "no such file" in with "corrupt file".

## Goals / Non-Goals

**Goals:**
- One message shape for input-file failures: names the file, the role it plays, and the cause.
- No traceback for a missing, directory, unreadable, or non-JSON input file on any CLI path.
- JSON-contract scripts report it as a typed error, not a crash.

**Non-Goals:**
- Schema-validation messages (already handled by `plan.py validate`).
- Output-file write failures, subprocess failures, CadQuery script errors (already typed).
- Changing exit codes or removing/renaming JSON keys.

## Decisions

- **Single helper in `units.py`**: `InputFileError(Exception)` plus `read_json(path, role)`; `load_plan(path)` becomes `read_json(path, "BUILD_PLAN.json")`. `units.py` is already imported by every affected script, so no new module. Alternative (a new `fileio.py`) rejected: one function does not need a module.
- **Message format**: `<role> not found: <path>`, `<role> is a directory, expected a file: <path>`, `cannot read <role> <path>: <os strerror>`, `<role> <path> is not valid JSON (line L, col C): <msg>`. Built from `FileNotFoundError` / `IsADirectoryError` / `PermissionError` / `JSONDecodeError`, with a generic `OSError` fallback.
- **CLI handling**: `InputFileError` subclasses `SystemExit`, so an uncaught one prints `error: <message>` to stderr and exits 1 with no per-script `main()` edits; `except Exception` handlers do not swallow it. Alternative (catch in every `main()`) rejected: eight identical try/excepts. `load_plan` is only called from `main()`s, so the in-process SystemExit is safe.
- **JSON-contract scripts**: catch `InputFileError` where the file is read and append `{"type": "file_error", "message": ..., "hint": ...}` to `errors`; hint says which flag/path to fix or which step produces the file.
- **STL**: keep raising `ValueError`, but check `os.path.isfile` first so the text says "STL not found: <path> (run with --deliver or the Model Export step to produce it)" versus "not a valid STL".
- **Existing local handlers** (`plan.py`, `printer_profile_validate.py`) switch to the helper so wording is uniform; their `Cannot load plan:` prefix is kept where tests assert on it.

## Risks / Trade-offs

- [Tests or Claude prompts match on old message text] -> grep tests and `skill/` for `Cannot load` before changing; keep prefixes that are asserted.
- [Broad `OSError` catch masks bugs] -> only wrap the open/read, not downstream processing.
