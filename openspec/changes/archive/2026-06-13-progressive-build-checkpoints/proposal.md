## Why

The Phase 3 part loop is fully autonomous: Claude writes a complete part script, validates, visually self-reviews, and only surfaces to the user on failure or after the attempt budget is exhausted. For a complex part this risks three silent iterations that drift from what the user actually wanted, with the first feedback opportunity coming only after the part is "done" (or stuck). The upstream `cad-skill` built in visible stages (base shape -> features -> finishing), pausing for user feedback at each: "Do NOT disappear and come back with a finished model." The cq-design rewrite traded that collaboration for autonomy. For simple parts autonomy is better; for complex parts an early human checkpoint catches wrong-direction work before it compounds.

## What Changes

- Add an optional progressive build mode to the Phase 3 part loop that constructs a complex part in visible stages, rendering a preview and pausing for user feedback between stages, instead of producing a finished part in one shot.
- Define a complexity gate that decides per part whether to build progressively or autonomously, so trivial parts are not slowed by checkpoints (e.g. number of `blocks_needed`, presence of `interfaces`, or part count threshold).
- Define the stage sequence (base shape -> features -> finishing) and what is shown at each checkpoint: the staged preview PNG plus a short summary of what was added, with the user able to approve, request a change, or skip remaining checkpoints for the part.
- Make the mode user-controllable: a default driven by the complexity gate, plus an explicit opt-in/opt-out (e.g. a flag or conversational signal) so the user can force progressive or force autonomous regardless of the gate.
- Update `SKILL.md` Phase 3 to document the gate, the stage sequence, the checkpoint interaction, and how progressive build composes with the existing per-stage geometry validation and visual self-review.

## Capabilities

### New Capabilities
- `progressive-build`: Staged construction of a complex part with user checkpoints between stages, including the complexity gate that selects the mode, the stage sequence, the checkpoint interaction (approve / change / skip), and how it composes with geometry validation and the visual self-review.

### Modified Capabilities
<!-- No existing spec covers the Phase 3 part-loop control flow; introducing progressive-build as a new capability. The visual-self-review capability is composed with, not modified by, this change. -->

## Impact

- `SKILL.md`: Phase 3 part loop (mode selection, stage sequence, checkpoint interaction), and the relationship to the existing Step 4 visual self-review.
- No `src/` code changes required: each stage is rendered and validated with the existing `run_cadquery_model.py --preview` over an intermediate `build/<part_id>.py`; staging is a Claude-driven authoring discipline, not new tooling.
- Composes with `visual-self-review` (the self-review checklist runs per stage and at completion) and `cq-preview-rendering` (produces the staged PNGs). The wrapper JSON contract is unchanged.
- Adds user-facing latency and interaction for complex parts by design; the complexity gate and opt-out keep simple parts fast.
