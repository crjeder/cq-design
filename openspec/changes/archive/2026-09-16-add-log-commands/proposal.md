## Why

The orchestrator currently appends to `build/journal.md` and `BUILD_PLAN.json`'s
`request_log` by hand-writing the line/JSON object itself in each phase file
(`skill/phase1_requirements.md`, `phase2_planning.md`, `phase3_build.md`, `phase4_deliver.md`).
This log-form authoring is repeated at every milestone and correction, and risks
inconsistent formatting (missing `ts`, wrong `kind`/`level` enum values, malformed
journal lines) that only surfaces later via `plan_validate.py` or a broken resume.
Small write commands remove that authoring step: Claude runs one command per log
entry instead of composing the line/JSON by hand.

## What Changes

- Add `journal.py append <journal_path> <phase>/<milestone> <text>`: appends a
  `- <phase>/<milestone>: <text>` line to `build/journal.md`, matching the format
  `skill/resume.md` already documents.
- Add an `add` subcommand to `src/request_log_search.py`: `request_log_search.py add
  <plan> --kind <clarification|correction> --text <text> [--level ...] [--target ...
  ...]`, which appends a validated entry to `BUILD_PLAN.json`'s `request_log` with
  `ts` set to the current UTC time automatically. The existing filter behavior moves
  under a `search` subcommand; existing flag names and JSON output are unchanged.
- Update `skill/phase3_build.md` (request log appending), `skill/phase1_requirements.md`,
  `skill/phase2_planning.md`, `skill/phase3_build.md`, `skill/phase4_deliver.md`
  (journal appending), and `reference/scripts.md` to call the new commands instead of
  describing hand-authored lines/JSON.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities
- `build-journal`: the skill SHALL append journal lines via `journal.py append`
  rather than hand-composing the line.
- `request-log-search`: `src/request_log_search.py` gains a `search` subcommand
  (previous default behavior, unchanged) and an `add` subcommand that appends a new
  `request_log` entry with an auto-generated `ts`.

## Impact

- `src/journal.py` (new)
- `src/request_log_search.py` (add `add` subcommand + subparser restructuring)
- `skill/phase1_requirements.md`, `skill/phase2_planning.md`, `skill/phase3_build.md`,
  `skill/phase4_deliver.md`, `skill/resume.md` (call sites / documented format)
- `reference/scripts.md` (CLI reference)
- `tests/test_request_log_search.py` (new `add` coverage), new `tests/test_journal.py`
