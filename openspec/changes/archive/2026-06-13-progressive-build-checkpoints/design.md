## Context

The Phase 3 part loop today, per part, attempts up to 3 times: render the part prompt, write the full `build/<part_id>.py`, run `run_cadquery_model.py --preview`, then Step 4 decides (geometry errors first, then the visual self-review, then done or retry or exhausted-fallback). The user is only consulted when the attempt budget is exhausted. This is efficient for simple parts but offers no early steering for complex ones.

`cad-skill` built each model in three visible phases with a user checkpoint after each. This change reintroduces that collaboration as an *opt-in, gated* mode layered on top of the existing loop rather than replacing it.

This is a documentation/workflow change. The stage rendering and validation reuse `run_cadquery_model.py --preview` exactly as the existing loop does; the only new artifact in `src/` would be none — staging is an authoring discipline Claude follows.

## Goals / Non-Goals

**Goals:**
- Give the user an early steering point on complex parts, before three autonomous iterations can drift.
- Keep simple parts fully autonomous and fast via a complexity gate.
- Compose cleanly with the existing per-attempt geometry validation and the `visual-self-review` checklist, reusing them per stage.
- Let the user force the mode either way regardless of the gate.

**Non-Goals:**
- No new `src/` tooling, no change to the `run_cadquery_model.py` JSON contract or error types.
- No mandatory checkpoints on every part (that is the regression this avoids).
- No change to the assembly phase or quality gate.
- No persistence of mode preference across sessions.

## Decisions

**Decision: Progressive build is gated, not default-on.**
A per-part complexity gate selects the mode. Proposed gate: build progressively when the part has at least one `interfaces` entry OR `blocks_needed` length is above a small threshold (e.g. >= 3); otherwise build autonomously. The exact threshold lives in SKILL.md so it can be tuned. Rationale: the cost of a checkpoint (latency + a user turn) is only justified when there is real risk of drift; a filleted box does not need one. Alternative considered: always progressive (rejected — regresses the autonomy cq-design deliberately added) and always autonomous with only the exhausted-budget fallback (rejected — that is today's gap).

**Decision: Three stages, base shape -> features -> finishing.**
Mirrors `cad-skill` and maps onto how CadQuery parts are naturally authored (outer shell, then boolean features/interfaces, then fillets/chamfers). Each stage writes the current `build/<part_id>.py`, renders, runs the visual self-review checklist scoped to what should exist at that stage, and pauses. Rationale: aligns the checkpoint boundaries with the points where direction errors are cheapest to fix. Alternative considered: a variable number of stages per feature — rejected as over-engineered and noisy.

**Decision: Checkpoint interaction is approve / request-change / skip-remaining.**
At each checkpoint Claude shows the staged preview PNG and a one-line summary of what the stage added, then waits. "Approve" advances to the next stage; "request change" re-authors the current stage with the feedback; "skip remaining" finishes the part autonomously (falls back to the normal loop for the rest). Rationale: gives control without forcing the user to babysit every stage. The skip path is what keeps a user who only wanted to check the base shape from being trapped in three prompts.

**Decision: Reuse the existing validation and visual self-review per stage.**
Each stage runs `run_cadquery_model.py --preview` and the `visual-self-review` checklist (scoped to the features expected so far). Geometry errors at a stage are fixed before the checkpoint is shown, so the user always reviews a valid stage. Rationale: no parallel validation path; the user reviews intent, the tooling reviews geometry. Trade-off: more validator invocations per complex part; acceptable given they only run in the gated/opt-in path.

**Decision: Mode is user-overridable.**
A conversational signal or flag forces progressive or autonomous regardless of the gate. Rationale: the gate is a heuristic; the user is the authority. Default remains gate-driven so no extra input is needed in the common case.

## Risks / Trade-offs

- **Checkpoints annoy users who wanted autonomy** -> Gate defaults conservatively (only genuinely complex parts), and "skip remaining" exits the staged flow in one turn; explicit opt-out forces autonomous.
- **Staged authoring diverges from the single-shot part prompt, producing different geometry than the autonomous path** -> The final stage must satisfy the same plan dimensions and the full visual self-review, so the end state is held to the same bar regardless of mode.
- **Added latency on multi-part builds** -> The gate is per part, so only the complex parts in a build incur checkpoints; simple parts in the same build stay fast.
- **Gate threshold is a guess** -> Keep the threshold and the gate condition stated in SKILL.md as tunable values, not buried, so they can be adjusted from field experience.
