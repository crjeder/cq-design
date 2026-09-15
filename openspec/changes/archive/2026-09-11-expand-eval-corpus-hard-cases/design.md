## Context

`evals/cases/` is 10 hand-authored single-round cases (9 single-part, 1
two-part with no joints). `evals/run_evals.py` scores a run directory by
matching produced STLs to golden STLs geometrically (Chamfer distance) and
folding `build/attempts.jsonl` telemetry into first-shot/attempts-to-pass/cost.
`evals/generate_goldens.py` builds golden meshes with small CadQuery builder
functions, one per case. None of this infrastructure assumes a case is
single-round or joint-free -- it is just that no case has ever exercised
`joints`, `kinematics`, or a second correction round, so `evals/run_evals.py`
`generate_case()` only ever starts `claude -p` in an empty working directory
with one `request.md` as the whole prompt.

`TODO.md`'s C5 defects (compass mixup, hinge-ear center-vs-edge, knuckle-pivot
ping-pong) are documented failures of exactly the shape the corpus is missing:
multi-part, shared-pivot, round-N correction. This change adds three cases
that exercise those shapes, plus the minimum runner change needed to generate
a round-2 case (seeding a working directory from a prior accepted state).

## Goals / Non-Goals

**Goals:**
- Add one case with `joints` + `kinematics` + a shared-pivot interface between
  two parts, scored by the existing Chamfer/first-shot pipeline unmodified.
- Add one case that starts generation from an existing accepted plan/script
  and applies a second-round correction, so `first_shot_rate` and
  `mean_chamfer_mm` can reflect regressions in correction-round handling
  (hand-duplicated literals, relative-wording misapplied as absolute).
- Add one case whose request prose mixes viewing-station and face-normal
  compass language for the same feature, scored against a golden built
  strictly on the fixed `prompts/planning.md` convention.
- Keep every existing scoring/runner contract (`score_case`, the scorecard
  JSON/markdown shape, `--cases`/`--generate` flags) unchanged, so the 10
  existing cases and every historical `evals/runs/*/scorecard.json` stay
  comparable.

**Non-Goals:**
- Implementing any of `TODO.md`'s `#c5-fixes-did-not-take-2026-09-08` product
  fixes (`coordinate_frame` schema field, hand-rolled-hinge lint, broadened
  `check_shared_interfaces`, `/retrofit`). This change only adds eval
  coverage; those fixes, whenever implemented, get their own change and will
  show up in these cases' scores.
- A general multi-round eval framework (N rounds, branching corrections,
  per-round scoring). Exactly one seed round -> one correction round, scored
  once at the end, matching the minimum shape needed to catch the C5 class.
- Changing how `score_case` works. A correction-round case's *final* state is
  still just produced STLs vs. golden STLs -- no new metric is needed to
  detect "the correction broke something," because Chamfer against the
  post-correction golden already fails when it does.

## Decisions

**Shared-pivot case uses `blocks.joints.pin_hinge`, not a hand-rolled knuckle.**
The C5 defect was a hand-rolled hinge with a hardcoded pivot literal
duplicated across two part scripts, with `joints`/`kinematics` left null even
though the plan called for a revolute pin hinge. The new case's golden
`BUILD_PLAN.json` uses `pin_hinge`'s two `emits` members inside a `joints`
entry with a shared `root_part`-derived pose, plus a `kinematics` entry
sweeping the hinge's declared range -- i.e., the golden plan is what C5's plan
*should* have been. This makes the case double as a regression guard on the
sanctioned mechanism itself (`mate_chain.py` deriving the second part's pose),
not just on Chamfer distance.

**Round-2 correction uses a `seed/` directory + `generate_case()` seed-copy,
not a synthetic multi-turn prompt.** Two options were considered: (a) encode
the whole two-round conversation as one long prompt to `claude -p` ("first
build X, then apply this correction to it"), or (b) actually seed a working
directory with a prior round's `BUILD_PLAN.json`/part script/`build/` state
and run `claude -p` with only the correction text as the prompt, matching how
a real second session starts (per `skill/resume.md`'s resume-from-disk model).
(b) is chosen: it exercises the real code path (an existing `BUILD_PLAN.json`
on disk, a correction `request_log` entry) rather than asking the model to
simulate two rounds in one turn, which would not catch a regression in how
the skill *reads back* prior state.

Implementation: a case directory may contain `seed/` holding whatever
`generate_case()` should copy into the case's working directory before
invoking `claude -p` (typically `BUILD_PLAN.json`, the part script(s), and
`printer_profile.json`). `generate_case()` checks for `seed/` and, if present,
copies its contents into `case_run_dir` first. The prompt wrapper text changes
only in referring to "this correction" when `seed/` is present; the request
text itself (`request.md`) is still the verbatim thing appended, so a
correction case's `request.md` reads as a correction, not a fresh spec (e.g.
"the lid wall is too thin at 1mm -- make it 2mm and keep the lip fit"). Score
mode is untouched: it never calls `generate_case()`, so scoring a
pre-generated correction-round run works exactly like any other case.

**Compass case has no new `coordinate_frame` machinery.** Since that field
does not exist yet (`TODO.md` marks it proposed, not implemented), this case
cannot test a *non-default* frame -- there is only one frame today. Instead it
tests the documented confusion mode directly: request prose that names a
feature both by viewing station ("visible in the South view") and by face
normal ("on the East-facing wall") in a way that, per `#c5-compass-language`,
resolves to *opposite* sides if conflated. The golden is built on the one true
convention (North=+Y, East=+X, "viewed from South" = camera at -Y looking
toward +Y), so a plan that flips the axis binding shows up as a large Chamfer
distance (the feature lands on the wrong face) rather than a subtle one.

**Corpus-size bound raised to `8 <= len <= 15`, not removed.** The test exists
to catch accidental bloat/shrinkage, not to cap the corpus at 10 forever;
13 cases (10 existing + 3 new) needs the bound moved, and 15 leaves headroom
for one or two more additions before the test needs touching again.

## Risks / Trade-offs

[Golden authoring for the hinge case requires hand-building `pin_hinge`
geometry in `evals/generate_goldens.py` without running the full skill
pipeline, risking a golden that does not match what `pin_hinge` actually
emits] -> mitigate by calling `blocks.joints.pin_hinge` directly inside the
golden builder (same as the block a correct plan would invoke), not
reimplementing hinge geometry by hand.

[A round-2 correction case is more expensive to maintain than a single-round
one -- two authored states instead of one] -> accept the cost; it is the
minimum needed to exercise the correction-round failure class at all. Scope
is capped at one seed + one correction (not a growing chain).

[Chamfer-only scoring cannot tell *why* a case failed -- a hinge case failing
Chamfer does not distinguish "wrong pivot" from "wrong wall thickness"] ->
accepted for this change (Non-Goal: no new metric). The existing
`chamfer_mm`/`matched_to` per-part breakdown in the scorecard already
localizes which produced part diverged; that is enough signal to investigate
manually, and adding joint-specific diagnostics is separable future work.

## Migration Plan

Additive only: new case directories, new golden builders, one `if` branch in
`generate_case()` guarded by `seed/` existing, one widened test bound. No
existing case, script, or scorecard field changes shape. Rollback is deleting
the three new case directories and reverting the two touched files.

## Open Questions

- Exact case directory names (`hinged-latch`, `lid-thickness-correction`,
  `east-side-mount` used as working names above) -- finalized during tasks
  based on what reads clearly next to the existing corpus's names
  (`sliding-lid`, `snap-lid`, `two-part-box`).
