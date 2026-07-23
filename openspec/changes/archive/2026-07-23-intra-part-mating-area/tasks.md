## 1. `cq_verify.py` helper

- [x] 1.1 Implement `verify_backed(backer, feature, axis, label="", tolerance=0.1)` in
      `src/cq_verify.py`: parse the signed axis token, compute the feature's contact
      coordinate, run the reach check against `backer`'s bbox, run the containment check
      on the two orthogonal axes, raise `[cq-verify:unbacked_mate:<label>] ...` on
      failure (naming which check failed and, for containment, which orthogonal axis),
      return `feature` unchanged on success.
- [x] 1.2 Update the module docstring's helper list to include `verify_backed` alongside
      `verify_boolean` / `verify_feature_bounds` / `check_workplane` / `verify_stage`.

## 2. Wrapper error mapping

- [x] 2.1 Add `"unbacked_mate"` to `run_cadquery_model.py`'s `_VERIFY_MARKER_RE`
      classification table (alongside `silent_boolean` / `feature_overflow` /
      `workplane_drift` / `stage_mismatch`), with a `type`/`message`/`hint` shape
      consistent with the existing entries.

## 3. Tests

- [x] 3.1 Add `verify_backed` unit tests (extended `tests/test_run_wrapper.py`, matching
      how `verify_boolean` / `verify_stage` are currently tested -- end-to-end through the
      wrapper, no direct-unit `test_cq_verify.py` exists for the other helpers either):
      fully-backed passes; containment failure on an orthogonal axis raises; reach
      failure raises; error message names the `label` and the failing check.
- [x] 3.2 Reproduce the historical cradle.py bug as a regression case: two boxes shaped
      like the pre-ROUND-7 leg/standoff (leg stopping short in Y, standoff centered past
      it) fail `verify_backed`; the ROUND-7-fixed dimensions (leg extended to
      `LEG_TIP_Y`) pass. (`test_unbacked_mate_end_to_end` /
      `test_verify_backed_passes_when_fully_backed`)
- [x] 3.3 Add/extend a wrapper-level test asserting a script raising
      `[cq-verify:unbacked_mate:...]` produces an `errors` entry with
      `"type": "unbacked_mate"` in `run_cadquery_model.py`'s JSON output.
      (`test_translate_stderr_classifies_verify_markers` extended;
      `test_unbacked_mate_end_to_end` covers it end-to-end.)

## 4. Guidance

- [x] 4.1 Add the `verify_backed` bullet to `prompts/part.md`'s "Construction-time
      verification" section, with a short example (standoff backed by leg) alongside the
      existing `verify_boolean`/`check_workplane` examples.
- [x] 4.2 Mirror the same guidance in `SKILL.md`'s generated-script rules (also added the
      `unbacked_mate` row to the error-handling reference table).
- [x] 4.3 Cross-check `CLAUDE.md`'s `src/cq_verify.py` table entry (the one-line summary
      of the module's exports) picks up `verify_backed` so the file inventory stays
      accurate. (Noticed `verify_stage` was already missing from that same row,
      pre-existing and out of scope here -- flagged as a separate background task rather
      than folded into this change.)

## 5. Backlog note

- [x] 5.1 Update `TODO.md`'s existing "design error: the llm often places the center of
      a box where actually a wall should sit" line: mark it addressed by this change for
      the intra-part case, name the `2026-07-01-joint-contract` archived change and
      explain why its inter-union half remains unimplemented (blocked on the
      satisfaction-algebra and sub-body-naming cruxes), and record the open crux --
      whether `verify_backed` generalizes upward into that design or stays separate --
      as a pointer for whoever revisits it next.

## 6. Validation

- [x] 6.1 Run `uv run pytest tests/` and confirm the new/extended tests pass alongside
      the existing `cq_verify`-adjacent suite. Full suite: 597 passed in 253s, no
      failures or regressions.
- [x] 6.2 Manually re-run (or re-derive) the C5 Phone-Holder cradle build with
      `verify_backed` added to `leg_and_ear`'s standoff construction, confirming it would
      have failed on the pre-ROUND-7 dimensions and passes on the current ones.
      Reproduced with the actual `build/cradle.py` constants (not just synthetic test
      numbers) in a scratch script run through `run_cadquery_model.py`: `LEG_TIP_Y=5.0`
      (pre-fix) raises `unbacked_mate` reporting "feature range [4.00, 6.00] mm exceeds
      backer range [-15.00, 5.00] mm" on Y; `LEG_TIP_Y=6.0` (current) passes with no
      errors. The C5 Phone-Holder project itself is a separate delivered design output,
      not part of this repo, so its `build/cradle.py` was not edited in place.
