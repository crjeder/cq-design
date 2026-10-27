# step-edit-command Specification

## Purpose
`/cq-design:edit`: apply a described change to an existing STEP/BREP solid in its own coordinate frame, verified by a mesh diff against the input, delivered as `out/<stem>_edited.step`.
## Requirements
### Requirement: Edit command reads a solid and a change description

`/cq-design:edit <file> <change description>` SHALL accept a `.step`/`.stp` or `.brep` file (`cq.importers.importStep` / `importBrep`; CadQuery has no IGES importer) and a free-text change description. It SHALL stop with a one-line message, writing nothing, when the file does not exist, has another extension, or the description is empty. It SHALL perform the init steps first when `init_permissions.py --check` reports the directory uninitialized, like `/cq-design:design`.

#### Scenario: STEP input
- **WHEN** `/cq-design:edit input.step add a 5 mm through hole at the centre of the top face` runs
- **THEN** the command proceeds to author the edit script

#### Scenario: Unsupported file
- **WHEN** the file argument is `part.stl`
- **THEN** the command stops, saying only STEP/BREP are accepted, and writes no file

#### Scenario: No description
- **WHEN** only a file is given
- **THEN** the command stops and asks for the change description

### Requirement: One edit script on the imported body

The command SHALL write exactly two scripts: `build/edit_input.py`, whose `result` is the unmodified imported file, and `build/<stem>_edited.py`, whose `result` is the imported file with the change applied. `build/<stem>_edited.py` SHALL import the file with the matching `cq.importers` function and SHALL modify it only by operations on that imported body (boolean cut/union with authored features, or face/edge operations on it); it SHALL NOT rebuild the part from scratch. Both scripts SHALL reference the input by path, never embed its geometry. The command SHALL NOT run phases 0-2 and SHALL NOT write `BUILD_PLAN.json`.

#### Scenario: Hole added
- **WHEN** the change adds a hole
- **THEN** `build/<stem>_edited.py` imports the file and cuts a cylinder from the imported body

#### Scenario: No plan
- **WHEN** the command finishes
- **THEN** no `BUILD_PLAN.json` was written or read

### Requirement: Input frame preserved

The edited result SHALL stay in the input file's coordinate frame: neither script SHALL translate, rotate or re-centre the imported body, and delivery SHALL NOT apply a print-orientation rotation. Directions in the change description ("top", "left") SHALL be read in the input frame (+Z up, +Y north per `SKILL.md`), and the command SHALL state that reading in its report.

#### Scenario: Unchanged geometry stays put
- **WHEN** the change only adds a feature on one face
- **THEN** every vertex of the input that the change does not touch has the same coordinates in the delivered file

#### Scenario: No print pose
- **WHEN** the result is delivered
- **THEN** `run_cadquery_model.py` was not passed `--print-rotate` and `print_orientation.py` was not run

### Requirement: Validate and diff before delivery

The command SHALL run `run_cadquery_model.py build/<stem>_edited.py --preview` and iterate on the script until `success` is true. It SHALL then mesh both scripts (`--deliver --formats stl --output-dir build/edit_diff`) and run `diff_models.py` on input (A) and result (B) with `--png`. When `identical` is true the edit SHALL be treated as not applied and iterated on. When the diff's changed volume (`only_a_volume`, `only_b_volume`) or `bbox_delta` contradicts the description (for example, material removed when the change only adds, or the bounding box grows when the change is internal), the command SHALL iterate. The command SHALL compare the input and result previews and the diff PNG before delivery. After 5 failed iterations it SHALL stop and report the last errors and diff instead of delivering.

#### Scenario: Edit had no effect
- **WHEN** `diff_models.py` reports `identical: true`
- **THEN** the command revises `build/<stem>_edited.py` and does not deliver

#### Scenario: Wrong direction
- **WHEN** the change says "add a boss" and the diff shows only `only_a_volume` (material removed)
- **THEN** the command revises `build/<stem>_edited.py`

#### Scenario: Gives up
- **WHEN** 5 iterations fail
- **THEN** no file is written to `out/` and the report shows the last errors and diff

### Requirement: Edited file delivered

On success the command SHALL write `out/<stem>_edited.step` (`<stem>` = input file name without extension) via `run_cadquery_model.py build/<stem>_edited.py --deliver --formats step --output-dir out`, and SHALL never overwrite the input file. The report SHALL list the delivered path, the diff volumes and `bbox_delta`, the diff PNG, and the direction reading used.

#### Scenario: Delivered
- **WHEN** the diff is consistent with the description
- **THEN** `out/input_edited.step` exists, `input.step` is unchanged, and the report lists the diff numbers

### Requirement: CADGenBench edit fixtures use the edit command

`evals/cadgenbench_run.py` SHALL build the prompt for a fixture that has `edit_description.txt` as a `/cq-design:edit input.step <description>` invocation (with the existing unattended and fidelity preamble, minus the fidelity text's `build/build.py --formats step` delivery instruction, which applies to generation only), and SHALL keep the generation prompt for other fixtures unchanged. `delivered_steps` SHALL continue to pick the result from `out/`.

#### Scenario: Edit fixture prompt
- **WHEN** a fixture directory contains `edit_description.txt` with text `T`
- **THEN** `build_prompt` returns a prompt containing `/cq-design:edit input.step` followed by `T`, and not `build/build.py`

#### Scenario: Generation fixture prompt
- **WHEN** a fixture has no `edit_description.txt`
- **THEN** `build_prompt` returns the drawing-reproduction prompt as before

