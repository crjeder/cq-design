## Why

Every LLM in the skill changes a script by rewriting its text with the Edit/Write tools,
so one wrong `old_string` or a whole-file rewrite can silently change or drop code the
edit was never meant to touch, and nothing checks the result before it lands on disk.
Parametric CAD tools avoid this by having every client (UI, scripts, agents) change the
model only through typed commands that address one feature by id and are validated before
they apply. The skill's scripts already have that shape: step scripts are groups of
`select`/`resize`/`place` per plan instance id, and edit scripts are a short sequence of
operations on an imported body.

## What Changes

- New `src/script_ops.py`: a command interface over a script's **groups**, the units an
  LLM edits.
  - Step part script: one group per plan instance (its `select` / `resize` / `place`
    calls and the position arithmetic between them), addressed by instance id.
  - Edit-command script and any script with `# step: <name>` markers: one group per
    marked section, addressed by name.
  - Legacy part script without markers: one group, `whole`.
  - Header (imports, `Part(...)`) and tail (`result = ...`) are fixed regions.
- Commands: `list`, `show`, `new` (first write, from a template or code file),
  `replace`, `insert`, `remove`, `move`. Code is passed as a file path, never inline on
  the command line.
- Every command preflights before writing: the result parses, the command touched only
  the addressed group, the group's identity is intact, every name a group reads is
  assigned earlier (so `remove`/`move` cannot strand a local), and `script_lint.py`
  passes (`--step` for step scripts). A refused command leaves the file byte-identical
  and returns a typed error.
- Each applied command is recorded in script history as a `command` event (depends on
  change `script-history-restore`), so every command is undoable with
  `script_history.py restore @prev`.
- `step_worker.py run` and `run_cadquery_model.py` report `unmanaged_edit: true` when the
  script's hash matches no `command`, `restore` or `new` event, i.e. it was changed by a
  text edit. The flag is a warning, not a failure.
- Instructions: `prompts/builder.md` and `commands/edit.md` change scripts only through
  `script_ops.py`, never with Edit/Write on the script; `skill/phase3_build.md` surfaces
  `unmanaged_edit` from a builder's last run report.

## Capabilities

### New Capabilities
- `script-ops`: group model of part and edit scripts, the edit command set, preflight
  checks, and unmanaged-edit detection.

### Modified Capabilities
- `step-edit-command`: the edit script is written with `# step:` sections and changed
  only through `script_ops.py`.
- `step-worker`: the run report carries `unmanaged_edit`.

## Impact

- New `src/script_ops.py` (stdlib `ast`; reuses `script_lint.py`); `src/step_worker.py`
  and `src/run_cadquery_model.py` (`unmanaged_edit`); `src/script_history.py` (`command`
  event, from `script-history-restore`).
- `prompts/builder.md`, `commands/edit.md`, `skill/phase3_build.md`, `reference/scripts.md`,
  `FILES.md`, `src/skill_permissions.json`.
- Tests: new `tests/test_script_ops.py` (no CadQuery needed); `tests/test_step_worker.py`,
  `tests/test_run_wrapper.py`.
- Requires `script-history-restore` to land first.
- Not a sandbox: a text edit to a script is still possible. It is detected and reported,
  not prevented, because the PostToolUse hook does not see builder sub-agent tool calls.
