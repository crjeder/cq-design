## 1. Exporter

- [x] 1.1 Add `src/regen_prompt.py` (stdlib only): `render(plan, *, parameters_src=None,
      sketches=None)` returning the Markdown, plus a `--plan/--out` CLI that discovers
      `parameters.py` and `sketches/` relative to the plan's directory and writes to
      stdout when `--out` is omitted. Exit 0 success, 1 on missing file / invalid JSON,
      matching `request_log_search.py`'s CLI shape.
- [x] 1.2 Render the sections in order: header instruction, `What to build` (the plan's
      `intent`), request history, sourced measurements, drawings, print target,
      previous decomposition labelled reference-only.
- [x] 1.3 Omit the history, measurements and drawings sections when their source is
      absent; escape `|` in part descriptions so the parts table stays well-formed.

## 2. Tests

- [x] 2.1 Add `tests/test_regen_prompt.py` (fast, no CadQuery): intent/history/targets/
      constraints/joints present; optional sections omitted when absent; parameters and
      sketches embedded; CLI writes the file and picks up both side artifacts; a missing
      plan returns 1.

## 3. Pipeline wiring

- [x] 3.1 Add Phase 4 step 6 to `skill/phase4_deliver.md`: run the exporter, overwrite on
      every delivery, do not hand-author, and read the result -- a bare-noun-phrase
      `What to build` means `intent` is stale and is fixed in the plan, not in the export.
- [x] 3.2 Add the `README.md` pointer to Phase 4 step 5 and update the
      `phase4/delivered` journal line.
- [x] 3.3 Add `REGENERATE.md` to the deliverable tree in `skill/phase3_build.md`'s
      **Model export** section; leave the `lib/` bundle list unchanged (snapshot artifact,
      not a build dependency).
- [x] 3.4 Update `SKILL.md`'s Phase 4 summary to name the export.

## 4. Documentation

- [x] 4.1 Add the contract row to `reference/scripts.md` and the one-line entries to
      `CLAUDE.md`'s script index, File Layout, and test list.
- [x] 4.2 Document the artifact in `README.md` (what it is, when it is written, how to
      re-export it by hand).
- [x] 4.3 Mark both `TODO.md` items done (`Intent-based prompt reformulation` was already
      delivered by `approved-intent-reformulation`; the export half is this change) and
      record the outcome in their Details sections.

## 5. Verification

- [x] 5.1 `uv run pytest tests/test_regen_prompt.py` passes; `ruff check` / `ruff format`
      clean on both new files.
- [x] 5.2 Full suite `uv run pytest tests/` passes (801 passed).
- [x] 5.3 Smoke-render an eval-corpus plan (`evals/cases/u-clip/BUILD_PLAN.json`) and
      confirm the output reads as a usable standalone request.
- [x] 5.4 `openspec validate regeneration-prompt-export --strict` passes.
