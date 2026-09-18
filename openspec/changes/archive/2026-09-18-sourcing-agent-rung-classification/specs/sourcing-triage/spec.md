## MODIFIED Requirements

### Requirement: Decision ladder classifies the best find
Phase 0 SHALL classify search results against a five-rung decision ladder, evaluated top-down, taking the first rung that fits:

1. Found parametric source (CadQuery, build123d, OpenSCAD, FreeCAD) - reuse or convert.
2. Found STEP/BREP/IGES - import as a dumb solid.
3. Found mesh that fits as-is - deliver it through measurement and the quality gate.
4. Found mesh that is close - measure and rebuild only the tractable subset.
5. Nothing usable - proceed with the current pipeline from Phase 1.

The Sourcing agent (see `sourcing-prompt-rendering`) SHALL assign a `Rung` per candidate
in its return table: `1` for `Kind` in {cadquery, build123d, openscad, freecad}, `2` for
`Kind` in {step, brep, iges}, and for `Kind: mesh` a provisional `3?` (stated dimensions
appear to match the request as-is), `4?` (a tractable discrepancy is named), or `n/a`
(the mismatch appears freeform/organic). The main session SHALL trust a `1` or `2` rung
outright, the same as it trusts the license `Reusable` verdict, without re-deriving it
from `Kind` itself. A `3?`/`4?` rung is provisional: the main session SHALL confirm it
via the rung 3/4 vetting steps (measurement, quality gate stages, user confirmation)
before treating it as final, and MAY downgrade a `3?` to rung 4 or fall through to
Phase 1 when vetting does not confirm it.

Candidates SHALL be collected before classification so a better-rung find from any source wins over a worse-rung find.

#### Scenario: Parametric source outranks a mesh
- **WHEN** the search finds both a fitting STL and a fitting OpenSCAD source for the same request
- **THEN** Phase 0 selects rung 1 (the parametric source)

#### Scenario: Nothing usable falls through to the pipeline
- **WHEN** no found model fits the request at rungs 1-4
- **THEN** Phase 0 ends and the pipeline proceeds with Phase 1 unchanged

#### Scenario: Agent-assigned rung 1 is trusted
- **WHEN** the Sourcing agent returns a candidate with `Kind: cadquery` and `Rung: 1`
- **THEN** the main session takes rung 1 for that candidate without re-deriving the
  classification from `Kind` itself

#### Scenario: Provisional mesh rung is confirmed by vetting
- **WHEN** the Sourcing agent returns a mesh candidate with `Rung: 3?`
- **THEN** the main session runs `measure_stl.py` and the quality gate's mesh-level
  stages, and only finalizes rung 3 (with user confirmation) if they pass

#### Scenario: Provisional mesh rung is downgraded
- **WHEN** a `Rung: 3?` candidate fails the measurement cross-check or a gate stage
- **THEN** rung 3 does not fit and classification continues down the ladder as today

---

### Requirement: Parametric source reuse and conversion
At rung 1, a build123d source SHALL be converted to CadQuery mechanically, assisted by `src/convert_build123d.py`, and the converted script SHALL be validated through `run_cadquery_model.py` like any generated part. An OpenSCAD source SHALL NOT be transpiled; the .scad file SHALL be used as the authoritative topology and parameter source and the part re-authored in CadQuery through the normal part loop. A CadQuery source SHALL be reused directly, adapted to the request's parameters.

Rung 1 handling begins once the Sourcing agent's `Rung: 1` is taken for a candidate (see
"Decision ladder classifies the best find"); no kind-based re-derivation precedes it.

#### Scenario: build123d source found
- **WHEN** rung 1 matches a build123d script
- **THEN** the script is converted to CadQuery with the converter helper and validated via the wrapper before delivery

#### Scenario: OpenSCAD source found
- **WHEN** rung 1 matches an OpenSCAD file
- **THEN** the part is re-authored in CadQuery using the .scad's topology and parameter values, and no textual transpilation of the .scad is attempted

---

### Requirement: BREP import is scoped as a dumb solid
At rung 2, a found STEP/BREP/IGES file SHALL be imported via `cq.importers` and used only as a mating reference or a base for boolean modification. The result SHALL be described to the user as non-reparametrizable.

Rung 2 handling begins once the Sourcing agent's `Rung: 2` is taken for a candidate; no
kind-based re-derivation precedes it.

#### Scenario: STEP file used as mating reference
- **WHEN** rung 2 matches a STEP file for a commercial part the model must mate with
- **THEN** the imported solid is used as reference or boolean input, and the delivery notes state the imported body is a dumb solid
