## 0. Prerequisite

- [x] 0.1 Change `script-history-restore` is implemented (`src/script_history.py` with blob store, event log and `restore`)

## 1. Group model (`src/script_ops.py`)

- [x] 1.1 `ast`-based split into header, groups, tail: instance groups by `select(id=...)` (including `if part.has("X"):` blocks), `# step: <name>` section groups, `whole` fallback
- [x] 1.2 `list` and `show` commands (JSON out)
- [x] 1.3 Tests in `tests/test_script_ops.py` over every `templates/*.py` (group ids and order; `lid_snap` double place; `enclosure_body` guard) and a marked edit script

## 2. Commands and preflight

- [x] 2.1 `new` (`--template` sets the `Part` id, `--code`, refuses existing without `--force`), `replace`, `insert`, `remove`, `move`; code from a file path only
- [x] 2.2 Preflight in order: `parse_error`, `group_identity`, `scope_violation` (source comparison of everything outside the addressed group), `undefined_local` (top-level def-before-use; comprehension targets local), `unknown_instance` (plan `blocks_needed`), `script_lint.py` (`--step` for step scripts); atomic write
- [x] 2.3 Append a `command` event (command, group, `src`) through `script_history` on every applied command
- [x] 2.4 Tests: each refusal leaves the file byte-identical; `replace` changes only its group; `insert`/`move` order; `remove` blocked by a dependent local; raw CadQuery refused; `restore @prev` undoes a command

## 3. Unmanaged-edit detection

- [x] 3.1 Shared helper in `script_history.py`: current hash vs `src` of `command` / `new` / `restore` events -> `unmanaged_edit`
- [x] 3.2 `src/step_worker.py` report and `run` event carry `unmanaged_edit` (warm and fallback); `src/run_cadquery_model.py` adds the key without touching `success`, `errors` or exit code
- [x] 3.3 Tests in `tests/test_step_worker.py` and `tests/test_run_wrapper.py`: text edit after a command -> true; no command events -> false

## 4. Instructions

- [x] 4.1 `prompts/builder.md`: create with `script_ops.py new`, add instances with `insert`, fix with `replace`, undo with `script_history.py restore`; write code to `build/<part>.op.py`; never Edit/Write `build/<part>.py`
- [x] 4.2 `commands/edit.md`: steps 1-2 use `script_ops.py new --code` with `# step:` sections; revisions in step 4 use section commands
- [x] 4.3 `skill/phase3_build.md`: report `unmanaged_edit: true` from a builder's step report with the part's decisions
- [x] 4.4 Verify `render_prompt.py builder` output contains the commands and no direct-edit instruction

## 5. Wiring and docs

- [x] 5.1 `src/skill_permissions.json`: allow `script_ops.py` in both path forms
- [x] 5.2 `reference/scripts.md` entry for `script_ops.py`; `unmanaged_edit` in the `step_worker.py` and `run_cadquery_model.py` entries; `FILES.md` lines for the script and test
- [x] 5.3 `uv run pytest tests/test_script_ops.py tests/test_step_worker.py tests/test_run_wrapper.py`; `ruff check --fix` and `ruff format` on changed files
