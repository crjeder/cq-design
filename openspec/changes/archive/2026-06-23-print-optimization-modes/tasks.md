## 1. Schema and plan validation

- [x] 1.1 In `src/build_plan_schema.json`, add a top-level optional `optimize_for`
      (`enum: ["strength", "min_support", "visual_quality"]`, default documented as
      `strength`) and the same optional `optimize_for` on each `parts[]` item.
- [x] 1.2 In `src/build_plan_schema.json`, add an optional per-part `show_face` object
      mirroring `load`: `{ "dir": [x, y, z] }` (3-number authored-frame outward normal),
      `additionalProperties: false`.
- [x] 1.3 In `src/plan_validate.py`, accept the new fields; no extra cross-check is required
      beyond schema, but confirm a plan/part-level `optimize_for` and a `show_face` pass and
      that an unknown `optimize_for` value fails with a descriptive error.

## 2. Visual scoring in print_orientation.py

- [x] 2.1 Add module constants: `SUPPORT_BAND` (mm2), `VISUAL_BAND`, `FLAT_EPS_DEG`, and
      `VISUAL_INCLINE_WEIGHT`; reuse the 45-degree gentle-incline threshold (a constant, not
      a magic literal).
- [x] 2.2 Add `_gentle_incline_fraction(posed_mesh)`: fraction of non-bed face area whose
      normal makes an angle with +Z or -Z inside `(FLAT_EPS_DEG, 45)` degrees (exclude
      near-flat and near-vertical; exclude bed-contact faces, reusing the contact mask logic
      from `_support_metrics`).
- [x] 2.3 Add `_infer_show_face(mesh)`: outward normal of the largest planar face (analogous
      to `_infer_load_dir`), returning a unit vector in the authored frame.
- [x] 2.4 Add `_visual_score(mesh, rotation, show_face_dir)`: returns `(visual, cosmetic_down,
      gentle_incline_fraction)` where `cosmetic_down = max(0, dot(R @ show_face, -Z))` and
      `visual = cosmetic_down - VISUAL_INCLINE_WEIGHT * gentle_incline_fraction`.

## 3. Mode-driven selection

- [x] 3.1 Extend the candidate dicts in `optimize_orientation` to also carry `visual`,
      `cosmetic_down`, and `gentle_incline_fraction` (scored for every candidate regardless
      of mode).
- [x] 3.2 Replace `_select(candidates, strength_band)` with a mode-aware selector keyed on
      `optimize_for`: `strength` (existing order), `min_support` (support primary within
      `SUPPORT_BAND`, then strength, then bed contact), `visual_quality` (visual primary
      within `VISUAL_BAND`, then strength, then support). Keep `idx` as the final
      deterministic tiebreak in all modes.
- [x] 3.3 Add `optimize_for: str = "strength"` and `show_face: list[float] | None = None`
      params to `optimize_orientation`; infer `show_face` when None and record
      `show_face_inferred`. Validate `optimize_for` against the allowed set.
- [x] 3.4 Extend the result dict with `visual_score` (+ `cosmetic_down`,
      `gentle_incline_fraction`), `optimize_for`, `show_face`, `show_face_inferred`, and
      update `rationale` to name the active mode and the winning trade-off.

## 4. CLI and build script plumbing

- [x] 4.1 Add `--optimize-for {strength,min_support,visual_quality}` (default `strength`) and
      `--show-face x,y,z` to `print_orientation.py`'s `main()`, parsing `--show-face` like
      `--load` and passing both into `optimize_orientation`.
- [x] 4.2 In `src/build_template.py`, compute each part's effective mode (part-level
      `optimize_for` else plan-level else `strength`) and its `show_face` and pass them into
      `optimize_orientation` on the recompute path (`_orientation_for` /
      `resolve_orientations`); the `orientations.json` reuse path is unchanged. Update the
      module docstring's "strength first, support second" line to say the recompute honors
      the plan's `optimize_for`.

## 5. Skill and prompt updates

- [x] 5.1 In `SKILL.md` "Print-orientation optimization", replace the "objective is fixed and
      ordered" wording with the three selectable modes, how the user's request sets
      `optimize_for` (plan-level + per-part), the `--optimize-for`/`--show-face` flags, and
      mode-specific loop guidance (visual_quality may accept weaker/higher-support poses by
      intent).
- [x] 5.2 In `prompts/planning.md`, instruct the LLM to record the user's stated optimization
      priority as `optimize_for` (and a `show_face` when the user identifies a display
      surface), defaulting to `strength` when unstated.
- [x] 5.3 If the planning summary lists optimization-relevant fields, surface the effective
      `optimize_for` (and any `show_face`) in the summary per the planning-phase spec.

## 6. Tests

- [x] 6.1 `tests/test_plan_validate.py`: plan-level `optimize_for`, per-part `optimize_for`
      override, per-part `show_face` all validate; an invalid `optimize_for` value is
      rejected; a plan omitting both still validates.
- [x] 6.2 Add a print-orientation test: a mesh where the three modes select different poses,
      asserting each mode picks the expected candidate (strength-best, min-support-best,
      visual-best).
- [x] 6.3 Add a visual-scoring test: a candidate with the cosmetic face down scores higher
      than the same part with it up; a candidate with more shallow-incline area scores lower.
- [x] 6.4 Add a determinism test: same mesh + mode run twice returns identical recommendation
      and scores.
- [x] 6.5 Add a `show_face` test: declared `show_face` drives the cosmetic-down reward, and an
      omitted one sets `show_face_inferred: true`.

## 7. Verify

- [x] 7.1 Run `uv run pytest tests/` and confirm new and existing tests pass.
- [x] 7.2 Run `openspec validate "print-optimization-modes" --strict`.
- [x] 7.3 Run `ruff check --fix` and `ruff format` on `src/print_orientation.py`,
      `src/plan_validate.py`, `src/build_template.py`, and the new tests.
