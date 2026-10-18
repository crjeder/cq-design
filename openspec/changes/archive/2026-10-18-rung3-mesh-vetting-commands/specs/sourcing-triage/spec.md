## MODIFIED Requirements


### Requirement: Decision ladder classifies the best find
Phase 0 SHALL classify search results against a five-rung decision ladder, evaluated top-down, taking the first rung that fits:

1. Found parametric source (CadQuery, build123d, OpenSCAD, FreeCAD) - reuse or convert.
2. Found STEP/BREP/IGES - import as a dumb solid.
3. Found mesh that fits as-is - deliver it through measurement and the bare-mesh checks.
4. Found mesh that is close - measure and rebuild only the tractable subset.
5. Nothing usable - proceed with the current pipeline from Phase 1.

The Sourcing agent (see `sourcing-prompt-rendering`) SHALL assign a `Rung` per candidate
in its return table: `1` for `Kind` in {cadquery, build123d, openscad, freecad}, `2` for
`Kind` in {step, brep, iges}, and for `Kind: mesh` a provisional `3?` (stated dimensions
appear to match the request as-is), `4?` (a tractable discrepancy is named), or `n/a`
(the mismatch appears freeform/organic). The main session SHALL trust a `1` or `2` rung
outright, the same as it trusts the license `Reusable` verdict, without re-deriving it
from `Kind` itself. A `3?`/`4?` rung is provisional: the main session SHALL confirm it
via the rung 3/4 vetting steps (measurement, bare-mesh watertightness and overhang checks,
user confirmation)
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
- **THEN** the main session runs `measure_stl.py` and `print_orientation.py` on the
  mesh, and only finalizes rung 3 (with user confirmation) if the measurement
  cross-check and watertightness pass

#### Scenario: Provisional mesh rung is downgraded
- **WHEN** a `Rung: 3?` candidate fails the measurement cross-check or is not watertight
- **THEN** rung 3 does not fit and classification continues down the ladder as today

### Requirement: Found meshes are vetted before delivery
At rung 3, the found mesh SHALL be run through `measure_stl.py` and its measured dimensions cross-checked against the request. Watertightness SHALL be read from that same `measure_stl.py` result (`is_watertight`); a mesh that is not watertight, or that fails to load, SHALL fail rung 3. Overhang SHALL be checked with `print_orientation.py <stl> --overhang-max-deg <n> --optimize-for min_support`, with `<n>` taken from `profile.json` `constraints.overhang_max_deg`; a nonzero `support_score` SHALL be reported to the user at confirmation (with the chosen pose's `rotate`) and SHALL NOT by itself fail rung 3. The vetting SHALL NOT invoke `quality_gate.py`, which requires a part script and a build plan that rung 3 does not have. The user SHALL confirm the found model (with its link) before it is delivered as the result.

#### Scenario: Found mesh fits and passes
- **WHEN** a found STL's measured dimensions match the request, `is_watertight` is true, and `support_score` is 0
- **THEN** the mesh is presented for confirmation and, once confirmed, delivered as the result with source link and license, and Phases 1-3 are skipped

#### Scenario: Found mesh fails the gate
- **WHEN** the `measure_stl.py` result for the found STL has `is_watertight: false`
- **THEN** rung 3 does not fit and classification continues down the ladder

#### Scenario: Found mesh needs support
- **WHEN** a found STL is watertight and matches the request but `print_orientation.py` reports a nonzero `support_score`
- **THEN** the user is told the mesh needs support in its best pose at the confirmation step, and the user's answer decides whether rung 3 is taken

#### Scenario: No gate invocation on a bare mesh
- **WHEN** rung 3 vetting runs
- **THEN** no `quality_gate.py` command is run and no `--help` is run to discover one
