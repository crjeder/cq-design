## Context

The Phase 3 part loop today is: render the part prompt, write `build/<part_id>.py`, run `run_cadquery_model.py --preview`, parse JSON, decide. The decision in Step 4 keys only on `success` and blocking geometry error types (`non_manifold_edge`, `non_watertight`, `dimension_mismatch`, `occ_exception`). The preview PNG is produced and displayed, but nothing in the loop compares it against design intent. The upstream `cad-skill` carried a `design-review.md` visual checklist that the cq-design rewrite dropped.

This change is documentation/workflow only. Rendering (`cq-preview-rendering`) and the wrapper JSON contract (`preview-and-validate`) already produce everything needed; the gap is a missing instruction telling Claude to look at the image.

## Goals / Non-Goals

**Goals:**
- Close the "passes all numeric checks but is the wrong shape" gap with a Claude-driven visual inspection step in the part loop.
- Reuse the existing retry budget and conversational fallback rather than inventing a new control flow.
- Keep the check cheap: it runs over the preview PNG that is already rendered, no extra subprocess.

**Non-Goals:**
- No automated/ML image analysis or new `src/` code. The reviewer is Claude reading the PNG.
- No change to the `run_cadquery_model.py` JSON contract or error types.
- No mandatory mid-build user checkpoint (the autonomous part loop stays autonomous; the user is only consulted when retries are exhausted). Progressive per-phase user checkpoints are a separate possible change.

## Decisions

**Decision: Visual review is a Claude step, not wrapper output.**
The wrapper cannot judge whether a shape matches user intent; only Claude (with the plan in context) can. Recording `visual_mismatch` in the loop rather than emitting it from `run_cadquery_model.py` keeps the wrapper contract stable and avoids a brittle heuristic in Python. Alternative considered: an automated "render diff vs reference" check — rejected, there is no reference image to diff against for a novel part.

**Decision: Reuse the 3-attempt retry budget.**
A `visual_mismatch` feeds the same loop as geometry errors, so attempt count, targeted-fix behavior, and the exhausted-budget fallback are all unchanged. This avoids a parallel control structure. Trade-off: a part with both geometry churn and visual churn can exhaust 3 attempts faster; acceptable, the fallback already asks the user.

**Decision: Checklist lives in `reference/` and is injected, mirroring `FDM 3D Print Design Guidelines.md` and `CadQuery Pattern Reference.md`.**
Keeps SKILL.md concise and lets the checklist evolve independently. The part-loop setup section gains one more file to read into context. Alternative considered: inline the checklist in SKILL.md Step 4 — rejected, it bloats the procedural section and duplicates the reference-injection pattern already in use.

**Decision: Geometry errors take priority over visual review within an attempt.**
If geometry validation fails, the render is unreliable (or absent), so the visual review is skipped until geometry passes. This keeps the order deterministic and avoids reviewing a broken mesh.

## Risks / Trade-offs

- **Subjectivity of "matches intent" inflates retries or stalls** → Bound it with a concrete checklist (named items, not open-ended judgment) and the existing 3-attempt cap with conversational fallback; a single failed checklist item is a defined mismatch.
- **False mismatch on a correct part wastes an attempt** → The fallback lets the user accept the part as-is, so a stuck-but-correct part is recoverable in one exchange.
- **Drift between SKILL.md Step 4 wording and the spec** → Keep the `visual_mismatch` finding and the done-condition described once in the error reference and referenced from Step 4.
