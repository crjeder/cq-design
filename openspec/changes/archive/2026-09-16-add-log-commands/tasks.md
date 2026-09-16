## 1. journal.py

- [x] 1.1 Create `src/journal.py`: stdlib-only, `append <journal_path> <milestone>
      <text>` writes `- <milestone>: <text>\n`, appending to the file (creating it if
      absent). Exit codes: 0 success, 1 on error (e.g. unwritable path).
- [x] 1.2 Add `tests/test_journal.py`: append to a fresh file, append a second line and
      confirm the first is untouched, error path for an unwritable directory.

## 2. request_log_search.py add subcommand

- [x] 2.1 Restructure `src/request_log_search.py`'s CLI into `search` (existing
      behavior, flags unchanged) and `add` subcommands via `argparse` subparsers,
      keeping `search_request_log()` as the sole importable read function.
- [x] 2.2 Implement `add`: required `--kind` (`clarification`|`correction`,
      `initial` rejected with exit 1), required `--text`, optional `--level`
      (`functional`|`operation`|`parameter`), optional repeatable `--target`. Sets
      `ts` to `datetime.now(timezone.utc)` in ISO-8601. Loads `BUILD_PLAN.json`,
      appends the entry to `request_log` (creating the array if absent), validates
      the result against `src/build_plan_schema.json` before writing, writes the file
      back on success, and on validation failure exits 1 with the error on stderr and
      leaves the file unchanged.
- [x] 2.3 Update `tests/test_request_log_search.py`: adjust existing invocations to
      the `search` subcommand; add `add` coverage for a plain append, `--target`
      repeated, omitted `--level`/`--target`, `--kind initial` rejection, and a
      validation-failure case that leaves the file unchanged.

## 3. Call sites and docs

- [x] 3.1 `skill/phase3_build.md`: replace the hand-composed `request_log` entry
      description with `request_log_search.py add ...` usage.
- [x] 3.2 `skill/phase0_sourcing.md`, `skill/phase1_requirements.md`,
      `skill/phase2_planning.md`, `skill/phase3_build.md`, `skill/phase4_deliver.md`:
      replace hand-appended journal line instructions with `journal.py append ...`
      usage, covering every milestone in `skill/resume.md`'s milestone table
      (`phase0/rung_decision` through `phase4/delivered` -- 13 call sites total).
- [x] 3.3 `skill/resume.md`: note that lines are written via `journal.py append`
      (format itself unchanged).
- [x] 3.4 `reference/scripts.md`: add `journal.py` entry; update the
      `request_log_search.py` entry for the `search`/`add` subcommands.
- [x] 3.5 Grep the repo for other `request_log_search.py` invocations without a
      subcommand (docs, CLAUDE.md, skill_permissions.json) and update them to
      `search`. Updated `CLAUDE.md` (file layout entry + stale "no dedicated script"
      journal note) and `src/skill_permissions.json` (added `journal.py` allow
      patterns; `request_log_search.py *` wildcards already cover both subcommands).
      Four `openspec/specs/*.md` files (`visual-self-review`, `subagent-orchestration`,
      `request-relative-acceptance`, `preview-cross-sections`) also reference the old
      flat CLI in illustrative text but belong to capabilities this change does not
      declare as modified -- left as-is, flagged separately rather than expanding scope.

## 4. Verification

- [x] 4.1 `uv run pytest tests/test_journal.py tests/test_request_log_search.py`
- [x] 4.2 `uv run pytest tests/` (full suite, confirm no regression from the
      subcommand restructuring) -- 915 passed, 1 skipped
