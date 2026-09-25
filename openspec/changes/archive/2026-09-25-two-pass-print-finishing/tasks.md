## 1. print_up helper

- [x] 1.1 Add `src/blocks/print_frame.py` with `print_up()` (env `CQ_PRINT_ROTATE`, default +Z); export from `blocks/__init__.py` (a helper, not a block: no inventory entry; teardrop inventory params updated)
- [x] 1.2 Tests: unset, flipped X 180, sideways rotation

## 2. Blocks

- [x] 2.1 `teardrop_bore` / `teardrop_post`: accept `print_up=`; update inventory params
- [x] 2.2 Tests for both blocks under flipped print-up

## 3. Runner plumbing

- [x] 3.1 `run_cadquery_model.py --print-rotate <orientation.json>` sets the env for the model subprocess
- [x] 3.2 `edge_treatment_check.py` re-runs under the pose; `build_template.py` needs nothing (its orientation pass stays pose-free, export applies the pose); `exporters._load_result` takes `print_rotate`
- [x] 3.3 Tests: env reaches the script; default run unchanged

## 4. Finishing pass and guard

- [x] 4.1 Add a "Print finishing" section to `skill/phase3_build.md`: the finishing pass IS the pose-aware `model_export.py` re-load (no separate command), guard results in `pose_findings`
- [x] 4.2 Pose-stability guard: `print_finishing.pose_stability_finding` re-scores the finished solid inside `export_model`, advisory on `rotate` change; `orientation_for` moved there from `build_template.py`
- [x] 4.3 Stamp `rotate` in the export manifest; `freshness.pose_stale_ids` (not yet wired into the whole-model checks, which take no orientations)
- [x] 4.4 Tests for guard and staleness

## 5. Prompt

- [x] 5.1 `prompts/part.md`: route orientation-dependent features through `print_up()`-aware helpers; drop pose guessing
- [x] 5.2 Update the `horizontal_round_hole` lint hint to mention `print_up=`
- [x] 5.3 Refresh the related TODO.md entries
