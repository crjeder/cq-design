## MODIFIED Requirements

### Requirement: One edit script on the imported body

The command SHALL write exactly two scripts: `build/edit_input.py`, whose `result` is the imported file, and `build/<stem>_edited.py`, whose `result` is the imported file with the change applied. Both scripts SHALL import the file with `blocks.import_solid` (the checked import, which may repair an invalid input), never with `cq.importers` directly. `build/<stem>_edited.py` SHALL modify the imported body only by operations on it (boolean cut/union with authored features, or face/edge operations on it); it SHALL NOT rebuild the part from scratch. Both scripts SHALL reference the input by path, never embed its geometry. The command SHALL NOT run phases 0-2 and SHALL NOT write `BUILD_PLAN.json`. When `import_solid` repairs the input, the command's report SHALL quote the `[cq-design:step-repair]` line. When it raises `step_unrepairable`, the command SHALL stop, deliver nothing, and report the error. Both scripts SHALL be created with `script_ops.py new --code` and SHALL mark each operation with a `# step: <name>` line (`import` for the import); every later revision of `build/<stem>_edited.py` SHALL go through `script_ops.py` `replace`, `insert`, `remove` or `move` on those sections, never through a text edit of the script.

#### Scenario: Hole added
- **WHEN** the change adds a hole
- **THEN** `build/<stem>_edited.py` imports the file with `blocks.import_solid` and cuts a cylinder from the imported body

#### Scenario: No plan
- **WHEN** the command finishes
- **THEN** no `BUILD_PLAN.json` was written or read

#### Scenario: Invalid input repaired
- **WHEN** the input has zero-area faces that rung 1 removes
- **THEN** the edit proceeds on the repaired body and the report quotes the repair line

#### Scenario: Input cannot be repaired
- **WHEN** `build/edit_input.py` fails with `step_unrepairable`
- **THEN** the command stops without delivering and reports the error

#### Scenario: Revision through a section command
- **WHEN** the diff shows the added hole in the wrong place
- **THEN** the command rewrites only the `hole` section with `script_ops.py replace` and the `import` section is unchanged
