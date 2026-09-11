## 1. Schema: coordinate_frame

- [x] 1.1 Add `coordinate_frame` (optional object: `east`/`north`/`up`, each
      enum of `+x/-x/+y/-y/+z/-z`) to `src/build_plan_schema.json`.
- [x] 1.2 `tests/test_plan_validate.py`: schema accepts absence, a valid
      binding, and rejects an invalid axis token.

## 2. plan_validate.py: coordinate_frame advisory

- [x] 2.1 Add a compass-word scanner (word-boundary, case-insensitive:
      `north|south|east|west`) over `intent`, `planning_notes`, and
      `request_log[].text`.
- [x] 2.2 Add `check_coordinate_frame_usage(plan) -> list[str]`: one finding
      when the scanner matches and `coordinate_frame` is absent.
- [x] 2.3 Wire it into `main()` at the `check_block_thinness` advisory tier
      (printed after `BUILD_PLAN OK`, not part of `validate_plan`'s blocking
      errors).
- [x] 2.4 Tests: compass word in `intent` flags; compass word in
      `request_log` flags; `coordinate_frame` present silences; no compass
      word emits nothing.

## 3. plan_validate.py: broaden check_shared_interfaces (positional)

- [x] 3.1 Reuse `placement.transform_point` to compute each interface's
      assembled-frame position from `position_mm` + the owning part's
      `placement` (identity when absent).
- [x] 3.2 Reuse `feature_presence_check`'s position tolerance constant (or
      export it) for the coincidence check; add a small relative-diameter
      tolerance for `diameter_mm` comparison.
- [x] 3.3 Extend `check_shared_interfaces` (or add a sibling function called
      alongside it) to flag two parts with coincident round interfaces and no
      linking `joints` entry, independent of `name`.
- [x] 3.4 Ensure the existing named-interface behavior is unchanged (no
      regression on `check_shared_interfaces`'s current findings).
- [x] 3.5 Tests: coincident unnamed interfaces flag; joints entry silences;
      differing diameter/position does not flag; interfaces missing
      `position_mm`/`diameter_mm` are skipped.

## 4. plan_validate.py: hinge/pivot intent without joints

- [x] 4.1 Add a hinge-word scanner (`hinge|pivot|fold|articulat`) over
      `intent` and `request_log[].text`.
- [x] 4.2 Add `check_hinge_intent_without_joints(plan) -> list[str]`: one
      finding when the scanner matches, `len(parts) > 1`, and `joints` is
      absent/null/empty.
- [x] 4.3 Wire into `main()` at the same advisory tier.
- [x] 4.4 Tests: hinge language + no joints flags; joints present silences;
      single-part plan is exempt.

## 5. quality_gate.py: hinge-guard-lint stage

- [x] 5.1 Add a helper resolving whether a given union id is
      hinge-associated: `moving_union` of a `kinematics` entry with
      `type: "revolute"`, or a `members[].part` of a `joints` entry with
      `block == "pin_hinge"`.
- [x] 5.2 Add `_run_hinge_guard_stage(plan, script_path) -> list[dict]`:
      resolve this script's union(s) via `units.iter_unions(plan)`; for each
      hinge-associated union, AST-scan the script (reusing
      `script_lint.py`'s `_flatten_chain`/call-name helpers where they fit)
      for a call to `verify_seated`, `verify_backed`, or `pin_hinge`; emit a
      `make_issue("hinge_guard", "warning", "hinge_guard_missing", ...)`
      finding per hinge-associated union missing all three.
- [x] 5.3 Wire `_run_hinge_guard_stage` into `run_gate`, alongside
      `_run_feature_presence_stage`.
- [x] 5.4 Tests: hand-rolled hinge script with no guard call flags; script
      using `verify_seated`/`verify_backed`/`pin_hinge` is silent; non-hinge
      part is never checked; multi-union script only checks its
      hinge-associated union; `type: "spherical"` is not covered.

## 6. Prompt / checkpoint prose

- [x] 6.1 `prompts/planning.md`: document `coordinate_frame` near the
      Coordinate vocabulary table; when the user's request used compass
      language implying a non-standard binding, write it at the Phase 1
      exit checkpoint.
- [x] 6.2 `skill/phase1_requirements.md`: checkpoint step reads/writes
      `coordinate_frame`.
- [x] 6.3 `prompts/planning.md` rule 7 (shared-interface note): extend to
      mention the unnamed/positional case and the hinge-intent-without-joints
      finding.

## 7. Verification

- [x] 7.1 Run the full suite (`uv run pytest tests/`) — green.
- [x] 7.2 Run `plan_validate.py` against the eval corpus
      (`evals/cases/*/BUILD_PLAN.json`) and confirm no new advisory findings
      fire on the existing goldens (none use compass/hinge language without
      a corresponding `joints`/`coordinate_frame`, or the findings are
      correct and expected).
- [x] 7.3 `openspec validate absence-lints-and-coordinate-frame --strict`.
