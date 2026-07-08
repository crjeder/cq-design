## Context

Generated part scripts run under `run_cadquery_model.py`, which sets
`PYTHONPATH=<src>` so a script can `from blocks import ...`. The wrapper catches
exceptions from the model subprocess and emits the `structured-errors` JSON contract.
Silent boolean failures (a `.cut()`/`.union()` whose tool does not overlap) currently
throw nothing -- the script exits 0 and the missing feature is invisible until a
downstream watertight/dimension check flags an unrelated-looking symptom. The behavior
to catch it is already described in prose (`reference/emboss_text.md:30`, the Anti-
Patterns catalog) but never executed. Upstream `thereprocase/cad-skill` ships this as
`cq_debug_helpers.py`; the TODO records the chosen strategy as **reimplement** (upstream
declares no license, project is PolyForm Noncommercial).

## Goals / Non-Goals

**Goals:**
- A clean-room helper module the generated script imports and calls at construction time.
- Silent-boolean and feature-overflow failures surface as *typed* wrapper errors naming
  the offending feature, so the bounded `claude -p` fix loop gets a targeted correction.
- Zero new third-party dependency; no change to any existing JSON contract key.

**Non-Goals:**
- Auto-injecting verify calls into every boolean (the prompt guides *when*; the LLM
  writes them, same as it writes block imports).
- Step-snapshot debugging (`StepExporter` in the upstream file) -- out of scope for this
  change; revisit only if the part loop shows a need.
- Any gate-stage or post-export mesh analysis (this is construction-time, in-process).

## Decisions

**1. Standalone `src/cq_verify.py`, not a member of `blocks/`.**
The `blocks` package is geometry primitives that get selected in `blocks_needed` and
listed in `inventory.json`; a debug assertion is neither. A sibling module under `src/`
is import-visible via the same `PYTHONPATH` without polluting the block inventory or the
planning prompt. Alternative considered: add to `blocks/__init__` re-exports -- rejected,
it would imply the verifier is a design block a plan can request.

**2. No-op detected only when volume AND face-count AND centroid are all unchanged.**
Matches the upstream heuristic and avoids false positives: a boolean that relocates
equal-volume material still changes the centroid; one that reshapes without net volume
change still changes the face count. Requiring all three unchanged means "genuinely did
nothing." Tolerances: volume ~1e-3, centroid ~1e-2 mm (same order as the wrapper's
existing epsilon checks).

**3. Signal failure via `RuntimeError`, classified by the wrapper.**
The helper raises a plain `RuntimeError` with a parseable prefix (e.g. the `label` and
operation). `run_cadquery_model.py` already funnels subprocess exceptions into `errors`;
we add a branch that inspects the exception type/marker and maps to `silent_boolean` /
`feature_overflow` before the generic `occ_exception` fallback. Alternative considered: a
custom exception subclass imported by the wrapper -- rejected to avoid coupling the model
subprocess's importable surface to the wrapper; a sentinel marker on a stdlib exception
keeps the helper self-contained. The mapping SHALL be robust to a `RuntimeError` that did
NOT come from the helper (only the helper's marker triggers the typed classification).

**4. Return the post-operation solid on success** so the call chains inline:
`result = verify_boolean(body, body.cut(tool), "cut", "vent_slot")`. Keeps the generated
script readable and the verify opt-in per boolean. The workplane check follows the same
shape -- `wp = check_workplane(wp, "lid_top", expected_origin=(0, 0, 12))` returns the
workplane so the assertion sits inline in the build chain.

**5. Workplane check raises the same marked `RuntimeError`, not a `ValueError`.**
Upstream `debug_workplane` raises `ValueError` and also prints origin/normal. We
normalize all three helpers to one marked `RuntimeError` so the wrapper's classification
branch has a single exception type + marker to key on, and drop the unconditional
`print` (it would pollute the wrapper's captured `stdout`); the diagnostic detail
(expected/actual origin, drift) goes into the exception message instead, which is where
the wrapper reads it for the `workplane_drift` error. The check reads `wp.plane.origin`;
`expected_origin` is a caller-supplied point (the script author knows the intended
anchor), never inferred.

## Risks / Trade-offs

- **[LLM over- or under-wraps booleans]** → The prompt guidance names the concrete
  triggers (computed offset, off-center feature, text merge) rather than "wrap
  everything"; the spec includes a scenario for leaving a trivial union unwrapped so the
  guidance stays balanced.
- **[Centroid/volume tolerance too tight or too loose]** → Tolerances are the same order
  as existing wrapper epsilons; tests pin both a true no-op and a marginal effective
  boolean so a regression in the threshold is caught.
- **[Marker-based classification is brittle]** → Use an explicit, unambiguous marker the
  helper controls (not string-matching arbitrary messages); a non-verify `RuntimeError`
  falls through to the existing generic handling, which is the safe default.
- **[Adds a subprocess import]** → Module is stdlib + CadQuery only, so it cannot fail to
  import in an environment where any part script already runs.

## Open Questions

- Should `feature_overflow` be a hard (blocking) error or advisory? Leaning blocking:
  geometry poking past the declared body is almost always a real defect, and the fix loop
  can act on it. Revisit if field runs show legitimate intentional overflow.
