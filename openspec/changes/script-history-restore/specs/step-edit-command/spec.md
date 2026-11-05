## MODIFIED Requirements

### Requirement: Validate and diff before delivery

The command SHALL run `run_cadquery_model.py build/<stem>_edited.py --preview` and iterate on the script until `success` is true. It SHALL then mesh both scripts (`--deliver --formats stl --output-dir build/edit_diff`) and run `diff_models.py` on input (A) and result (B) with `--png`. When `identical` is true the edit SHALL be treated as not applied and iterated on. When the diff's changed volume (`only_a_volume`, `only_b_volume`) or `bbox_delta` contradicts the description (for example, material removed when the change only adds, or the bounding box grows when the change is internal), the command SHALL iterate. When a revision turns a run that had `success: true` into a failing one, or fails a diff check the previous revision passed, the command SHALL run `script_history.py restore @prev build/<stem>_edited.py` before revising again, and SHALL NOT revert the revision by editing the text back. The command SHALL compare the input and result previews and the diff PNG before delivery. After 5 failed iterations it SHALL stop and report the last errors and diff instead of delivering.

#### Scenario: Edit had no effect
- **WHEN** `diff_models.py` reports `identical: true`
- **THEN** the command revises `build/<stem>_edited.py` and does not deliver

#### Scenario: Wrong direction
- **WHEN** the change says "add a boss" and the diff shows only `only_a_volume` (material removed)
- **THEN** the command revises `build/<stem>_edited.py`

#### Scenario: A revision breaks a working script
- **WHEN** revision 2 succeeded but contradicted the diff, and revision 3 fails with `success: false`
- **THEN** the command restores `@prev` (revision 2's source) before writing revision 4

#### Scenario: Gives up
- **WHEN** 5 iterations fail
- **THEN** no file is written to `out/` and the report shows the last errors and diff
