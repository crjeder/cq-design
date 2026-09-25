## Context

Pipeline today: part loop (authoring, pose guessed) -> approval -> `print_orientation.py` (scores the authored STL) -> export -> gate. `edge_treatment_check` already rotates edges into the build frame post hoc but only warns. Orientation output carries `rotate` (authored -> build frame, placement convention). Scripts already re-run several times (validate, edge check, plate regeneration), so a re-run with extra input is cheap and deterministic.

## Goals / Non-Goals

**Goals:** resolve orientation-dependent treatments from the accepted pose without an LLM round; keep authoring-pass behavior unchanged; make staleness detectable.

**Non-Goals:** orientation-independent features (stress fillets, cosmetic rounding) stay at authoring; no new optimizer; no change to how orientation is scored; FEM/speed advisors unchanged (revisit later).

## Decisions

- **Env var, not script edit.** `CQ_PRINT_ROTATE` (JSON `rotate` list) read by `print_up()`. Alternative: a PARAMETERS entry rewritten per pass; rejected, it mutates the script and breaks `plan.py import-params` round-trips and script-hash stamps. Alternative: CLI arg to the script; rejected, scripts run via a runpy shim with no argv contract.
- **Direction in the authored frame.** `print_up()` is the inverse of the `rotate` transform applied to +Z, so features are authored in the frame the script already uses. Default +Z when unset.
- **Helpers classify, scripts don't.** `teardrop_*(print_up=)` and an edge-treatment helper take the vector; builders never branch on pose themselves. Alternative: post-process the solid (auto-add teardrops); rejected, it needs feature recognition, the same trap as the mesh-based edge classifier noted in `edge_treatment_check`.
- **Pose-stability guard.** After the finishing pass, re-run `print_orientation.py` on the new STL; if `rotate` differs from the accepted one, emit an advisory finding and keep the accepted pose. Finishing edits are tiny (about 0.01 cm3 for teardrops), so this should be rare.
- **Provenance.** `source_script_hash` covers script text only; the finishing pass changes geometry without changing text. Stamp the `rotate` used in the export manifest and treat a mismatch as stale.

## Risks / Trade-offs

- [Scripts that ignore `print_up()` gain nothing] -> prompt rule plus the existing `horizontal_round_hole` lint; behavior identical to today.
- [Circularity: orientation scored on a pessimistic mesh without teardrops] -> accepted; the guard catches material shifts.
- [Env var is hidden input] -> recorded in the manifest and journal; `--print-rotate` makes it explicit on the CLI.
- [Sideways print-up on blocks with a fixed +Y axis] -> `print_up=` handles the peak sign for axis-aligned cases only; general axes need cutter rotation by the builder (documented).

## Open Questions

- Is the finishing pass part of `model_export.py` or a separate step in `phase3_build.md`? Leaning separate, so it is skippable and inspectable.
- Should FEM/speed re-checks hook into the same pass?
