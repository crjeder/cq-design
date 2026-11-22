## MODIFIED Requirements

### Requirement: Validate and diff before delivery

The command SHALL run `run_cadquery_model.py build/<stem>_edited.py --preview` and iterate on the script until `success` is true. It SHALL then mesh both scripts (`--deliver --formats stl --output-dir build/edit_diff`) and run `diff_models.py` on input (A) and result (B) with `--png`, `--region` and `--expect-volume`. The region SHALL be measured from the imported input as the bounding box of the feature the description names, padded by at least 2 mm and including any feature the edit moves; `--expect-volume` SHALL be derived from the description's dimensions. When `identical` is true the edit SHALL be treated as not applied and iterated on. When the diff's changed volume (`only_a_volume`, `only_b_volume`) or `bbox_delta` contradicts the description (for example, material removed when the change only adds, or the bounding box grows when the change is internal), the command SHALL iterate. When `localized` is false, `volume_in_range` is false, or `region_fraction` exceeds 0.5, the command SHALL iterate (a region that large is re-measured tighter, not accepted). When a revision turns a run that had `success: true` into a failing one, or fails a diff check the previous revision passed, the command SHALL run `script_history.py restore @prev build/<stem>_edited.py` before revising again, and SHALL NOT revert the revision by editing the text back. The command SHALL compare the input and result previews and the diff PNG before delivery. After 5 failed iterations it SHALL fall back as in "Unverified edit falls back to the input".

#### Scenario: Edit had no effect
- **WHEN** `diff_models.py` reports `identical: true`
- **THEN** the command revises `build/<stem>_edited.py` and does not deliver the edit

#### Scenario: Wrong direction
- **WHEN** the change says "add a boss" and the diff shows only `only_a_volume` (material removed)
- **THEN** the command revises `build/<stem>_edited.py`

#### Scenario: Edit on the wrong feature
- **WHEN** the description names a boss but the diff reports `localized: false`
- **THEN** the command revises `build/<stem>_edited.py` and does not deliver the edit

#### Scenario: Volume change does not match
- **WHEN** the description implies a 3000 mm3 change and `volume_in_range` is false
- **THEN** the command revises `build/<stem>_edited.py`

#### Scenario: A revision breaks a working script
- **WHEN** revision 2 succeeded but contradicted the diff, and revision 3 fails with `success: false`
- **THEN** the command restores `@prev` (revision 2's source) before writing revision 4

#### Scenario: Gives up
- **WHEN** 5 iterations fail
- **THEN** the command falls back to the unchanged input and the report shows the last errors and diff

## ADDED Requirements

### Requirement: Unverified edit falls back to the input

When no revision passes the diff checks within 5 iterations, the command SHALL copy the original input file, byte for byte, to `out/<stem>_edited.step` and SHALL NOT deliver any edited body. The report SHALL state that the edit is unverified and the input was delivered unchanged, and list the last errors and diff numbers. The input file SHALL NOT be overwritten. A `step_unrepairable` input SHALL still deliver nothing.

#### Scenario: Retry budget exhausted
- **WHEN** 5 iterations end with `localized: false`
- **THEN** `out/input_edited.step` is byte-identical to `input.step` and the report says the edit is unverified

#### Scenario: Input unrepairable
- **WHEN** `build/edit_input.py` fails with `step_unrepairable`
- **THEN** nothing is written to `out/`
