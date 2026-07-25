# Sourcing Triage

## Purpose

Defines Phase 0 sourcing triage: searching for an existing model that answers
the user's request before any from-scratch design begins, and the decision
ladder that classifies and reuses what is found.

## Requirements

### Requirement: Phase 0 runs before requirements analysis
The skill SHALL provide a Phase 0 sourcing triage, documented in `skill/phase0_sourcing.md` and entered before Phase 1, that searches for existing models answering the user's request before any from-scratch design begins. The search SHALL reuse the model-platform search workflow defined in `skill/phase1_requirements.md` (web search plus Thingiverse, Printables, MakerWorld) by reference rather than duplicating it. The user SHALL be able to skip Phase 0 by requesting a from-scratch design explicitly.

#### Scenario: Standard request enters Phase 0 first
- **WHEN** the user requests a model without saying "design from scratch"
- **THEN** the skill reads `skill/phase0_sourcing.md` and performs the sourcing search before Phase 1 requirements analysis

#### Scenario: Explicit from-scratch request skips Phase 0
- **WHEN** the user asks to design the model from scratch
- **THEN** Phase 0 is skipped and the pipeline starts at Phase 1

#### Scenario: Custom-dimension request gets the quick pass
- **WHEN** the request is dominated by user-specific dimensions or interfaces
- **THEN** Phase 0 performs a single quick search pass rather than the full ladder before falling through to Phase 1

---

### Requirement: Decision ladder classifies the best find
Phase 0 SHALL classify search results against a five-rung decision ladder, evaluated top-down, taking the first rung that fits:

1. Found parametric source (CadQuery, build123d, OpenSCAD, FreeCAD) - reuse or convert.
2. Found STEP/BREP/IGES - import as a dumb solid.
3. Found mesh that fits as-is - deliver it through measurement and the quality gate.
4. Found mesh that is close - measure and rebuild only the tractable subset.
5. Nothing usable - proceed with the current pipeline from Phase 1.

Candidates SHALL be collected before classification so a better-rung find from any source wins over a worse-rung find.

#### Scenario: Parametric source outranks a mesh
- **WHEN** the search finds both a fitting STL and a fitting OpenSCAD source for the same request
- **THEN** Phase 0 selects rung 1 (the parametric source)

#### Scenario: Nothing usable falls through to the pipeline
- **WHEN** no found model fits the request at rungs 1-4
- **THEN** Phase 0 ends and the pipeline proceeds with Phase 1 unchanged

---

### Requirement: Parametric source reuse and conversion
At rung 1, a build123d source SHALL be converted to CadQuery mechanically, assisted by `src/convert_build123d.py`, and the converted script SHALL be validated through `run_cadquery_model.py` like any generated part. An OpenSCAD source SHALL NOT be transpiled; the .scad file SHALL be used as the authoritative topology and parameter source and the part re-authored in CadQuery through the normal part loop. A CadQuery source SHALL be reused directly, adapted to the request's parameters.

#### Scenario: build123d source found
- **WHEN** rung 1 matches a build123d script
- **THEN** the script is converted to CadQuery with the converter helper and validated via the wrapper before delivery

#### Scenario: OpenSCAD source found
- **WHEN** rung 1 matches an OpenSCAD file
- **THEN** the part is re-authored in CadQuery using the .scad's topology and parameter values, and no textual transpilation of the .scad is attempted

---

### Requirement: BREP import is scoped as a dumb solid
At rung 2, a found STEP/BREP/IGES file SHALL be imported via `cq.importers` and used only as a mating reference or a base for boolean modification. The result SHALL be described to the user as non-reparametrizable.

#### Scenario: STEP file used as mating reference
- **WHEN** rung 2 matches a STEP file for a commercial part the model must mate with
- **THEN** the imported solid is used as reference or boolean input, and the delivery notes state the imported body is a dumb solid

---

### Requirement: Found meshes are vetted before delivery
At rung 3, the found mesh SHALL be run through `measure_stl.py` and its measured dimensions cross-checked against the request, and SHALL pass the quality gate's mesh-level stages (watertightness, overhang) before delivery. The user SHALL confirm the found model (with its link) before it is delivered as the result.

#### Scenario: Found mesh fits and passes
- **WHEN** a found STL's measured dimensions match the request and the mesh passes watertightness and overhang checks
- **THEN** the mesh is delivered as the result, with source link and license, and Phases 1-3 are skipped

#### Scenario: Found mesh fails the gate
- **WHEN** the found STL is not watertight or fails the overhang check
- **THEN** rung 3 does not fit and classification continues down the ladder

---

### Requirement: Partial rebuild covers only the tractable subset
At rung 4, Phase 0 SHALL limit rebuilding to features `measure_stl.py` detects (extrusions, revolutions, axis-aligned features). General mesh-to-parametric reverse engineering SHALL NOT be attempted or promised.

#### Scenario: Close mesh with axis-aligned differences
- **WHEN** a found mesh matches except for a hole pattern that must move
- **THEN** the part is rebuilt parametrically using the mesh's measured dimensions as the source, via the normal pipeline

#### Scenario: Close mesh with freeform differences
- **WHEN** the difference lies in freeform/organic geometry `measure_stl.py` cannot characterize
- **THEN** rung 4 does not fit and the pipeline proceeds from Phase 1

---

### Requirement: License check is mandatory at reuse rungs
At rungs 1-4 the source model's license SHALL be identified before reuse. A missing or unstated license SHALL be treated as all-rights-reserved and the rung SHALL NOT fit. An ND (no-derivatives) license SHALL block rungs 1, 2, and 4; at rung 3 an ND mesh MAY be delivered unmodified only where the license permits redistribution, otherwise the user SHALL receive the source link instead of the file. The license name, source URL, and chosen rung SHALL be recorded - in `planning_notes` when a BUILD_PLAN exists, otherwise in the delivery summary - and shown to the user at the reuse decision.

#### Scenario: ND-licensed parametric source
- **WHEN** rung 1 matches a CC BY-ND licensed OpenSCAD source
- **THEN** rung 1 is rejected for that candidate and classification continues

#### Scenario: No license stated
- **WHEN** a found model page states no license
- **THEN** the candidate is treated as all-rights-reserved and not reused

#### Scenario: Provenance recorded
- **WHEN** any rung 1-4 reuse is accepted
- **THEN** the license, source URL, and rung are recorded in `planning_notes` (or the delivery summary when no plan exists) and stated to the user
