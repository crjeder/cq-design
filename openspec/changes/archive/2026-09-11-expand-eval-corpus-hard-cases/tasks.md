## 1. Runner: seed-directory support for correction-round cases

- [x] 1.1 In `evals/run_evals.py`'s `generate_case()`, before invoking
      `claude -p`, check for `<case>/seed/`; if present, copy its contents
      into `case_run_dir` (`shutil.copytree(..., dirs_exist_ok=True)`).
- [x] 1.2 When `seed/` is present, adjust the prompt wrapper text to frame the
      request as a correction to existing state (keep `request.md`'s content
      unmodified -- only the surrounding instruction text changes).
- [x] 1.3 Confirm score mode (no `--generate`) needs no changes -- it already
      scores whatever `<run-dir>/<case>/` contains regardless of how it got
      there. (Verified by reading `score_case`/`main`: neither touches
      `generate_case` or `seed/`.)

## 2. Hinged two-part case (joints + kinematics + shared pivot)

- [x] 2.1 Pick a case name and directory (`evals/cases/hinged-latch/`).
- [x] 2.2 Author `request.md`: a two-part request describing a hinge (leaf +
      base) with an explicit pivot and a folding range of motion.
- [x] 2.3 Author golden `BUILD_PLAN.json`: two parts, a `joints` entry using
      `blocks.joints.pin_hinge`'s two `emits` members with `root_part`-derived
      placement, a `kinematics` entry sweeping the declared hinge range, and a
      shared interface both parts reference for the pivot bore.
- [x] 2.4 Verify the plan validates (`plan_validate.validate_plan` -> `OK`).
- [x] 2.5 Add a golden builder to `evals/generate_goldens.py` that calls
      `blocks.joints.pin_hinge` directly (not hand-rolled geometry) for both
      members, and a `GOLDENS` entry for the case.
- [x] 2.6 Generate goldens: `uv run python evals/generate_goldens.py
      hinged-latch`.
- [x] 2.7 Author `case.json` (`tolerance_mm`, `expected_parts: 2`, tags).

## 3. Round-2 correction case

- [x] 3.1 Pick a case name and directory
      (`evals/cases/lid-thickness-correction/`).
- [x] 3.2 Author `seed/BUILD_PLAN.json` and `seed/corrected_lid.py`: a
      prior-round accepted single-part state (a lid with a 1mm-thin locating
      lip).
- [x] 3.3 Author `request.md` as a second-round correction against that seed
      (thicken the lip 1mm -> 2mm while preserving the footprint).
- [x] 3.4 Author golden `BUILD_PLAN.json` and `corrected_lid.py` reflecting
      the corrected state (lip thickened to 2mm), including `request_log`
      with `initial` + `correction` entries.
- [x] 3.5 Verify the corrected plan validates (both seed and golden plans ->
      `OK`).
- [x] 3.6 Add a golden builder + `GOLDENS` entry to `evals/generate_goldens.py`
      for the corrected geometry; generate goldens for the case.
- [x] 3.7 Author `case.json`.

## 4. Compass-wording case

- [x] 4.1 Pick a case name and directory (`evals/cases/east-side-mount/`).
- [x] 4.2 Author `request.md`: a single-part request naming one feature by
      both a viewing-station phrase and a face-normal phrase that would land
      on opposite sides if conflated (mirroring `#c5-compass-language`'s
      "viewed from South" vs. "East-facing" pattern).
- [x] 4.3 Author golden `BUILD_PLAN.json` with the feature placed per the
      fixed `prompts/planning.md` convention (North=+Y, East=+X).
- [x] 4.4 Verify the plan validates.
- [x] 4.5 Add a golden builder + `GOLDENS` entry to `evals/generate_goldens.py`;
      generate the golden mesh (bbox verified 60x40x14 mm, exact match).
- [x] 4.6 Author `case.json`.

## 5. Corpus-wide checks

- [x] 5.1 In `tests/test_eval_corpus.py`, raise `test_corpus_has_about_ten_cases`'s
      bound from `8 <= len <= 12` to `8 <= len <= 15`.
- [x] 5.2 Run `uv run pytest tests/test_eval_corpus.py` and confirm all three
      new cases pass `test_case_is_self_contained`,
      `test_case_plan_validates`, and `test_golden_bbox_matches_plan_dimensions`
      (40 passed).
- [x] 5.3 Run `uv run pytest tests/test_run_evals.py` to confirm the
      seed-copy change in `generate_case()` doesn't break existing
      score-mode tests (19 passed).
- [x] 5.4 Score mode sanity check: ran `evals/run_evals.py --run-dir <tmp>
      --cases hinged-latch,lid-thickness-correction,east-side-mount` against
      each case's own `golden/` as a stand-in run directory (golden STLs
      copied into `stl/`) -- all three report `chamfer 0.000 mm`
      (`within_tolerance` true); temp dir removed after.

## 6. Documentation

- [x] 6.1 Checked `CLAUDE.md` for an eval-corpus mention: none found (its
      script index lists `evals/run_evals.py` and `evals/generate_goldens.py`
      generically); left as-is.
- [x] 6.2 Cross-referenced the three new cases from `TODO.md`'s
      `#c5-fixes-did-not-take-2026-09-08` section, without checking off any
      of that section's product-fix items.
