## 1. diff_models checks

- [x] 1.1 Add `--region`, `--expect-volume`, `--outside-tol` to `src/diff_models.py`; compute `outside_volume`, `changed_bbox`, `volume_delta`, `localized`, `volume_in_range`, `region_fraction` (null when not requested)
- [x] 1.2 Add tests to `tests/test_diff_models.py`: change inside region, collateral change outside, volume out of range, flags absent (nulls), region equal to bbox

## 2. edit command

- [x] 2.1 Update `commands/edit.md` step 4: measure region from the imported input, derive expected volume, pass both flags, iterate on `localized` / `volume_in_range` / `region_fraction`
- [x] 2.2 Replace step 5's "deliver nothing" with the input-copy fallback and the "edit unverified" report line; keep `step_unrepairable` delivering nothing
- [x] 2.3 Update `tests/test_edit_command.py` if it asserts the old give-up text or diff flags

## 3. docs and calibration

- [x] 3.1 Update the `diff_models.py` row in `reference/scripts.md`
- [x] 3.2 Run `uv run pytest tests/test_diff_models.py tests/test_edit_command.py`
- [ ] 3.3 Calibrate `--outside-tol` on edit fixtures 202, 208, 244 and adjust the default if tessellation noise trips it
