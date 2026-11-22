## Why

Issue #394: on CADGenBench, 14 of 32 edit fixtures score at or below the unedited input. The grader renormalizes shape against the no-op, so a wrong edit gets shape 0 and the no-op itself scores about 0.4. `commands/edit.md` step 4 only rejects `identical: true` and edits whose volume sign or bbox contradicts the request, so a plausible edit on the wrong feature, or with collateral change elsewhere, is delivered.

## What Changes

- `diff_models.py` gains an optional localization check: `--region xmin,ymin,zmin,xmax,ymax,zmax` and `--expect-volume LO,HI`. It reports how much changed material lies outside the region, the bbox of the changed material, the net volume change, and whether each check passed. Without the flags the output is unchanged apart from new `null` keys.
- `commands/edit.md` step 4 measures the named feature's region from the imported input, passes it with the expected volume change, and revises when the edit is not localized or the volume change is out of range.
- When the edit cannot be verified within the 5-iteration budget, the command delivers the input unchanged as `out/<stem>_edited.step` instead of delivering nothing, and the report says the edit is unverified.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-diff`: adds the region and expected-volume checks and their output keys.
- `step-edit-command`: "Validate and diff before delivery" requires the localization check; giving up delivers the unchanged input instead of nothing.

## Impact

- `src/diff_models.py`, `tests/test_diff_models.py`, `commands/edit.md`, `reference/scripts.md` (diff_models row).
- `evals/cadgenbench_run.py` needs no change: `delivered_steps` already reads `out/`.
- Does not fix why the edits land on the wrong feature (not verified in #394); it stops delivering them. #347 (visual diff) is related and untouched.
