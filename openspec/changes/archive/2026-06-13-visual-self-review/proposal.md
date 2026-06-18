## Why

The pipeline validates geometry numerically (watertightness, bounding box, overhang angle, wall thickness) but never instructs Claude to look at the rendered preview and confirm it matches the user's intent. A model can pass every automated check and still be the wrong shape: a feature on the wrong face, a mirrored cutout, a missing port, or wrong proportions. The upstream `cad-skill` had a `design-review.md` visual checklist; the cq-design rewrite dropped it without replacement. This is the one correctness gap the automated gate cannot close.

## What Changes

- Add a visual self-review step to the Phase 3 part loop: after a part passes geometry validation and a preview PNG is produced, Claude inspects the rendered image against a structured checklist before marking the part done.
- Add a reusable visual-review checklist as an injected reference (e.g. `reference/Visual Review Checklist.md`) covering shape match, feature completeness, proportional accuracy, no floating/disconnected bodies, flat bed face, and orientation.
- Define a new error/finding type (e.g. `visual_mismatch`) so a failed visual review feeds the existing retry loop the same way geometry errors do, with the mismatch description used to drive the corrective edit.
- Update `SKILL.md` Phase 3 Step 4 ("Decide") so a part is only "done" when geometry validation passes AND the visual review confirms intent; a visual mismatch within the attempt budget triggers a targeted fix.
- Document the visual-review step and `visual_mismatch` finding in the SKILL error-handling reference.

## Capabilities

### New Capabilities
- `visual-self-review`: Claude's structured inspection of the rendered preview against design intent during the part loop, including the checklist contents, the pass/mismatch decision, and how a mismatch feeds the retry loop.

### Modified Capabilities
<!-- No existing spec covers the Phase 3 part-loop decision; introducing visual-self-review as a new capability. -->

## Impact

- `SKILL.md`: Phase 3 part loop (Step 4 decision), error-handling reference table, reference-injection list.
- `reference/`: new `Visual Review Checklist.md` injected into the part loop.
- No `src/` code changes required: rendering and JSON contract are unchanged; the review is a Claude-driven step over the already-produced preview PNG. The `visual_mismatch` finding is recorded by Claude in the loop, not emitted by `run_cadquery_model.py`.
- Related specs for context: `cq-preview-rendering` (produces the PNG), `preview-and-validate` (geometry/error contract), `reference-injection` (how the checklist reaches the prompt).
