## Why

`evals/cases/` (the `eval-harness` spec's canonical corpus) holds 10 cases: 9
single-part, 1 two-part, 0 with `joints`, 0 with `kinematics`, 0 with a
correction round, 0 that stress compass-direction wording. `TODO.md`'s C5
Phone-Holder defects -- compass-language mixup (`#c5-compass-language`), a
hinge ear placed center-aligned instead of tangent
(`#c5-hinge-ear-center-vs-edge`), and a shared-pivot literal that ping-ponged
across correction rounds because the plan never used `joints`/`mate_chain.py`
(`#c5-knuckle-pivot-ping-pong`) -- are all multi-part, shared-pivot,
round-N-correction failures. None of the current 10 cases can regress on any
of them: `first_shot_rate` sat at 0.7-0.85 across 14 recorded runs
(`evals/runs/*/scorecard.md`) while these real-world defects persisted through
three merged "fixes" that never landed on the affected project (`TODO.md`
`#c5-fixes-did-not-take-2026-09-08`). The scorecard is structurally blind to
the failure class it most needs to catch.

## What Changes

- Three new golden cases added to `evals/cases/`, each targeting one gap the
  current corpus cannot exercise:
  - A hinged two-part case (`hinged-latch` or similar): two parts joined by a
    `blocks.joints.pin_hinge` matched pair, a `joints` entry, a `kinematics`
    sweep entry, and a bore that both parts reference as a shared interface --
    the exact shape of the C5 knuckle-pivot defect.
  - A round-2 correction case (`lid-thickness-correction` or similar): the
    corpus gains a seed BUILD_PLAN.json + part script (a prior round's
    accepted state) and a second-round `request.md` phrased as a relative
    correction ("make the wall 1mm thicker", not a from-scratch spec) rather
    than an initial request -- so generation starts from an existing project,
    not an empty directory.
  - A compass-wording case (`east-side-mount` or similar): a single-part
    request whose prose mixes a viewing-station phrase ("viewed from South")
    with a face-normal phrase ("east-facing") for the same feature, the exact
    conflation named in `#c5-compass-language`, scored against a golden built
    strictly on the `prompts/planning.md` fixed convention (North=+Y,
    East=+X).
- `evals/generate_goldens.py` gains one builder per new case's part(s).
- `evals/run_evals.py`'s `generate_case()` gains seed-directory support: when
  a case directory has a `seed/` subdirectory, its contents are copied into
  the case's working directory before `claude -p` runs, and the prompt is
  built from the case's `request.md` as a correction-round delta instead of a
  from-scratch request. Score mode (no `--generate`) is unaffected -- it
  already scores whatever the run directory contains.
- `tests/test_eval_corpus.py`'s `test_corpus_has_about_ten_cases` bound is
  raised from `8 <= len <= 12` to `8 <= len <= 15` to admit 13 cases without
  losing its purpose (catching accidental corpus bloat/shrinkage).

Explicitly out of scope: the product-side fixes TODO.md's
`#c5-fixes-did-not-take-2026-09-08` proposes (a `coordinate_frame` schema
field, a hand-rolled-hinge lint, broadened `check_shared_interfaces`, a
`/retrofit` step). Those stay tracked in `TODO.md`. This change only adds the
eval coverage so that work -- once done -- has a scorecard signal to move.

## Capabilities

### New Capabilities
- none (this extends the existing `eval-harness` capability's corpus and
  runner; no new user-facing capability is introduced)

### Modified Capabilities
- `eval-harness`: corpus requirement extended to include at least one
  multi-part case with `joints`+`kinematics`+a shared pivot interface, at
  least one round-2 correction case seeded from a prior accepted state, and
  at least one case exercising ambiguous compass wording; `generate_case()`
  gains seed-directory support for correction-round cases.

## Impact

- `evals/cases/` -- 3 new case directories (`request.md`, `case.json`,
  `BUILD_PLAN.json`, `golden/*.stl`; the correction case also gets `seed/`).
- `evals/generate_goldens.py` -- 3 new builder functions, `GOLDENS` entries.
- `evals/run_evals.py` -- `generate_case()` seed-copy branch; no change to
  scoring, telemetry, or the JSON/markdown scorecard shape.
- `tests/test_eval_corpus.py` -- one bound updated.
- No change to `src/*.py` runtime behavior, `BUILD_PLAN.json` schema, or any
  block. Purely eval-corpus and eval-runner scope.
