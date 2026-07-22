# Design: Phase 0 Sourcing Triage

## Context

Today the pipeline always designs from scratch. Phase 1 already contains a mature model-platform search workflow (Thingiverse/Printables/MakerWorld, `skill/phase1_requirements.md` steps 1.1-1.8) - but it is used only to harvest dimensions; a found model's geometry is discarded. `measure_stl.py` already extracts bbox, layers, and cylinders from a downloaded STL. The quality gate already validates any mesh. The missing piece is a decision phase that runs before Phase 1 and can short-circuit the pipeline when a found model answers the request.

## Goals / Non-Goals

**Goals:**
- A Phase 0 decision ladder that classifies the best online find into one of five rungs and routes accordingly.
- Reuse, not duplication: the search workflow, `measure_stl.py`, and the quality gate are shared with Phase 1/4 as-is.
- Provenance and license recorded in `planning_notes` for every reuse rung.
- Requests resolved at rungs 1-3 never load Phase 2/3 machinery (token win).

**Non-Goals:**
- General mesh -> parametric reverse engineering (rung 4 covers only the tractable subset `measure_stl.py` detects).
- An OpenSCAD transpiler. The .scad is read as a topology/parameter source; geometry is re-authored in CadQuery by the normal part loop.
- Changes to `BUILD_PLAN.json` schema, the wrapper JSON contract, or any validation script.
- Automated license detection. The license is read from the model page by the LLM; the rule is that it MUST be read and recorded, not that software parses it.

## Decisions

**D1: Phase 0 is a skill phase file, not a Python tool.**
The triage is judgment (does this model fit? is the license OK?) plus browsing - exactly what the LLM + Playwright already do in Phase 1. New file `skill/phase0_sourcing.md`, referenced from SKILL.md's phase overview with the standard mandatory-read-at-entry rule. No `src/triage.py`. Alternative considered: a scoring script over `measure_stl.py` output - rejected; fit is request-relative and mostly non-geometric (license, printability, interface compatibility).

**D2: Ladder is evaluated top-down, first rung that fits wins.**
Order encodes preference: parametric source > BREP import > usable mesh > partial rebuild > scratch. A worse-rung find never blocks a better-rung find from a different source; the search collects candidates first, then classifies the best.

**D3: Search workflow is shared by reference, not copied.**
`skill/phase0_sourcing.md` points to the Phase 1 proprietary-interface search sequence (`skill/phase1_requirements.md`) rather than restating it. When Phase 0 ran and found nothing usable, Phase 1's dimension lookup may still reuse the same search results from context - no second sweep.

**D4: Rung 3 (mesh fits as-is) still goes through measurement + gate.**
Found models are frequently wrong or unprintable. The delivered mesh is run through `measure_stl.py` (dimensions cross-checked against the request) and the quality gate's mesh-level stages (watertightness, overhang). Deliverable is the vetted mesh, not a blind re-hosting.

**D5: Rung 2 (STEP/BREP/IGES) imports via `cq.importers` and is scoped as a dumb solid.**
Usable as a mating reference or boolean-modification base inside a normal part script; the plan's `planning_notes` state that the imported body is not reparametrizable. No new importer code - `cq.importers.importStep` exists; the phase file documents the pattern.

**D6: build123d conversion gets a small helper, OpenSCAD does not.**
`src/convert_build123d.py`: a mechanical assist (import-name and API-surface mapping notes + a runnable check that the converted script produces a solid via the existing wrapper). build123d and CadQuery are both OCC-based so conversion is mostly renaming; the helper keeps the known mappings in one place. OpenSCAD files are semantically distant (CSG tree, `hull()`/`minkowski()`/recursion have no BRep equivalent) - the phase file instructs re-authoring with the .scad as the parameter/topology reference, feeding the normal part loop.

**D7: License gate is mandatory and blocking at rungs 1-4.**
No license found = treated as all-rights-reserved = rung does not fit (fall through to the next rung or rung 5). ND licenses specifically block rungs 1, 2, and 4 (all involve derivation); an ND mesh delivered unmodified at rung 3 is permitted where the license allows redistribution, otherwise the user gets the link instead of the file. License + URL + chosen rung are recorded in `planning_notes`.

**D8: Provenance lives in `planning_notes`, no schema change.**
`planning_notes` is free-text and already schema-valid. A structured `provenance` field was considered and rejected for now: rungs 1-3 often produce no BUILD_PLAN at all (no build loop), so the invariant "provenance in the plan" only applies where a plan exists (rungs 1-express-as-plan, 4, and partial cases). Where no plan is generated, provenance goes in the delivery summary to the user.

## Risks / Trade-offs

- [Phase 0 adds latency to every request, including obviously-custom ones] -> The phase file includes a skip heuristic: requests dominated by user-specific dimensions/interfaces (the core cq-design case) get a single quick search pass, not the full ladder; the user can also say "design from scratch" to skip Phase 0 entirely.
- [Found models judged "fits as-is" may actually not fit user intent] -> Rung 3 requires the dimension cross-check via `measure_stl.py` against stated requirements, plus explicit user confirmation with the model preview/link before delivery.
- [License misreading] -> The license name and URL are recorded and shown to the user at the decision checkpoint; the user confirms reuse.
- [build123d helper drifts from upstream API] -> Helper is notes + a wrapper-backed smoke check, not a transpiler; drift shows up as a failed run, handled by the normal part loop.

## Open Questions

- Whether MakerWorld's license metadata is reliably scrapeable via accessibility snapshot (Printables and Thingiverse are). If not, the phase file falls back to "open the license page explicitly".
