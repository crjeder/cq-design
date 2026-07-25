# Phase 0: Sourcing Triage

## Why

The pipeline designs every model from scratch even when a proven, printable model already exists online - today's web lookup (Phase 1) only harvests dimensions from found models, then rebuilds anyway. cq-design's proper scope is the case where no usable parametric model exists; requests answerable by a found model should skip the build loop entirely, saving the full Phase 1-3 token and iteration cost and inheriting proven topology.

## What Changes

- Add a Phase 0 "sourcing triage" ahead of the current pipeline: a decision ladder evaluated top-down, taking the first rung that fits:
  1. **Found parametric source** (CadQuery, build123d, OpenSCAD, FreeCAD) -> reuse or convert. build123d -> CadQuery is mostly mechanical (both OCC-based); OpenSCAD is not transpiled - the .scad is the authoritative topology + parameter source, re-authored in CadQuery.
  2. **Found STEP/BREP/IGES** -> import via `cq.importers`; a dumb solid usable as a mating reference or for boolean modification, scoped as exactly that (not reparametrizable).
  3. **Found mesh that fits as-is** -> deliver it, still routed through `measure_stl.py` + the quality gate (found models are frequently wrong or unprintable).
  4. **Found mesh that's close** -> measure + rebuild only the tractable subset (extrusions, revolutions, axis-aligned features that `measure_stl.py` detects). General mesh->parametric reverse engineering is out of scope.
  5. **Nothing usable** -> current pipeline (Phase 1 onward), unchanged.
- Mandatory license check at rungs 1-4: ND licenses prohibit the convert-and-adapt step; license and source URL are recorded in `planning_notes`.
- New `skill/phase0_sourcing.md` with the triage detail, reusing the existing Thingiverse/Printables/MakerWorld search workflow from Phase 1.
- `prompts/planning.md` gains a provenance rule: when a plan derives from a found source, record source URL, license, and reuse rung in `planning_notes`.
- Small converter helper for build123d sources (rung 1 mechanical conversion aid).

## Capabilities

### New Capabilities

- `sourcing-triage`: the Phase 0 decision ladder - search for existing models before designing, classify the best find into one of five rungs, enforce the license check, and route each rung to its handling (reuse/convert, import, deliver-with-gate, partial rebuild, or full pipeline).

### Modified Capabilities

- `planning-phase`: planning records provenance (source URL, license, reuse rung) in `planning_notes` when the plan derives from a found source.
- `skill-doc-structure`: the phase file roster gains `skill/phase0_sourcing.md`; SKILL.md's phase overview gains Phase 0 with a pointer to it.

## Impact

- New files: `skill/phase0_sourcing.md`, `src/convert_build123d.py` (converter helper), templates as needed.
- Modified files: `SKILL.md` (Phase 0 section in the phase overview), `prompts/planning.md` (provenance rule), `skill/phase1_requirements.md` (cross-reference: dimension lookup vs. sourcing search).
- No changes to the JSON contract, `BUILD_PLAN.json` schema, or any `src/` check scripts; rung 3 reuses `measure_stl.py` and the quality gate as-is.
- Token cost: requests resolved at rungs 1-3 never load Phase 2/3 machinery.
