# script-ops Specification

## Purpose
TBD - created by syncing change script-edit-commands. Update Purpose after archive.
## Requirements

### Requirement: Scripts are parsed into addressable groups
`src/script_ops.py` SHALL split a script into a header, ordered groups and a tail. In a
step-form part script, a group SHALL be every top-level statement from a `select(...,
id=X)` up to the next `select` or the tail, addressed by instance id `X`; an
`if part.has("X"):` whose body holds only instance `X`'s statements SHALL belong to group
`X`. In any other script, a group SHALL run from a `# step: <name>` comment line to the
next marker or the tail, addressed by `<name>`; a script with neither SHALL be one group
named `whole`. The header SHALL be the statements before the first group. In a step script
the tail SHALL be a final top-level `result = ...` assignment after the last group; marked
and `whole` scripts SHALL have no tail (edit scripts reassign `result` in every section).
A group SHALL end at its last statement, so comments after it belong to the next region. `script_ops.py list <script>` SHALL print each
group's id, kind, line span and source hash, and `show <script> <group>` its source.

#### Scenario: Step script grouped by instance
- **WHEN** `list` runs on `templates/l_bracket_gusset.py`
- **THEN** it reports groups `arm_v`, `arm_h`, `gusset`, `hole_v`, `hole_h` in that order,
  with the `x, y, z = part.positions(...)` lines inside `hole_v` and `hole_h`

#### Scenario: Instance placed twice is one group
- **WHEN** `list` runs on `templates/lid_snap.py`
- **THEN** both `place(clip, ...)` calls belong to group `clip`

#### Scenario: Optional instance guard
- **WHEN** `list` runs on `templates/enclosure_body.py`
- **THEN** the `if part.has("boss"):` block is group `boss`

#### Scenario: Marked edit script
- **WHEN** a script has `# step: import` and `# step: hole` markers
- **THEN** `list` reports groups `import` and `hole`

### Requirement: Edits go through group commands
`script_ops.py` SHALL provide `new <script> (--template <file> | --code <file>)`,
`replace <script> <group> --code <file>`, `insert <script> (--after <group> | --first)
--code <file>`, `remove <script> <group>` and `move <script> <group> (--after <group> |
--first)`. Code SHALL be read only from a file path. `new` SHALL refuse an existing script
without `--force`, SHALL be the only command that writes the header and tail, and with
`--template` SHALL set the `Part("...")` id to the script's stem. Each command SHALL print
one JSON object with `success`, `command`, `group`, `changed_groups`, `errors` (each with
`type`, `message`, `hint`) and `src` (the resulting source hash).

#### Scenario: Replace one placement
- **WHEN** `replace build/plate.py hole_v --code build/plate.op.py` runs with a valid
  `hole_v` group
- **THEN** only group `hole_v` differs from the previous file and `changed_groups` is
  `["hole_v"]`

#### Scenario: Insert a new instance
- **WHEN** `insert build/plate.py --after hole_v --code build/plate.op.py` runs with a
  group for planned instance `slot`
- **THEN** group `slot` follows `hole_v` and every other line is unchanged

### Requirement: Commands are preflighted before writing
Before writing, each command SHALL check the candidate text and SHALL refuse with a typed
error, leaving the file byte-identical, on the first failure of: `parse_error` (does not
parse); `group_identity` (`replace`/`insert` code is not exactly one group, names another
group's id, or `insert` reuses an existing id); `scope_violation` (header, tail or any
group other than the addressed one differs from the current file); `undefined_local` (a
group reads a top-level name that the header, an earlier group or the group itself does
not assign); `unknown_instance` (a step-script group id that is not a `blocks_needed`
instance of the part in the project's `BUILD_PLAN.json`); and, for step scripts only,
`script_lint.py --step` findings, returned as the command's errors (edit and legacy
scripts are raw CadQuery, where lint's magic-number advice does not apply). On success it SHALL
write the file atomically.

#### Scenario: Code for the wrong group
- **WHEN** `replace hole_v` is given code whose `select` names `hole_h`
- **THEN** the command returns `group_identity` and the file is unchanged

#### Scenario: Removing a group another group depends on
- **WHEN** group `standoff` reads `top`, assigned only in group `plate`, and `remove plate`
  runs
- **THEN** the command returns `undefined_local` naming `top` and the file is unchanged

#### Scenario: Raw CadQuery in a step group
- **WHEN** `replace` code contains `cq.Workplane("XY").box(10, 10, 2)`
- **THEN** the command returns the `raw_cadquery` lint error and the file is unchanged

### Requirement: Applied commands are recorded and undoable
Every applied command (including `new`) SHALL append a `command` event with the command,
group and resulting `src` to the script's history log through `script_history`, storing
the resulting source blob, so `script_history.py restore @prev` undoes it.

#### Scenario: Undo a command
- **WHEN** a `replace` is applied and `script_history.py restore @prev` runs
- **THEN** the script equals its source before the `replace`

### Requirement: Text edits outside the commands are reported
`step_worker.py run` and `run_cadquery_model.py` SHALL report `"unmanaged_edit": true`
when the script's history log has at least one `command`, `new` or `restore` event and the
script's current hash equals none of their `src` values, and `false` otherwise, and SHALL
record the flag on the `run` event. The flag SHALL NOT change `success`, `errors` or the
exit code.

#### Scenario: Builder used the Edit tool
- **WHEN** a script was last changed by a `replace` and then edited as text
- **THEN** the next run reports `unmanaged_edit: true` and otherwise runs normally

#### Scenario: Untouched legacy project
- **WHEN** a script has no command events in its history
- **THEN** runs report `unmanaged_edit: false`

### Requirement: LLMs change scripts only through the commands
`prompts/builder.md` and `commands/edit.md` SHALL instruct the LLM to create and change
scripts only with `script_ops.py` and to undo with `script_history.py restore`, and SHALL
NOT instruct it to use Edit/Write on a script. `skill/phase3_build.md` SHALL tell the
orchestrator to report a builder whose saved step report has `unmanaged_edit: true` to the
user alongside the part's decisions.

#### Scenario: Builder prompt names the commands
- **WHEN** `render_prompt.py builder` renders a builder prompt
- **THEN** the prompt contains the `script_ops.py` `new`, `replace` and `insert` commands
  and no instruction to edit `build/<part>.py` directly
