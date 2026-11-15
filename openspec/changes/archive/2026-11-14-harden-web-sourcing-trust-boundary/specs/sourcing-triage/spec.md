## MODIFIED Requirements

### Requirement: Parametric source reuse and conversion
At rung 1, a found CadQuery or build123d source is third-party code. Before any such script
(or a script mechanically converted from it) is run, the main session SHALL show the user the
source URL, its license and a plain statement that reuse runs third-party Python on their
machine, and SHALL ask the user to choose between running it and re-authoring it. Only on
an explicit run choice SHALL a CadQuery source be reused directly, adapted to the request's
parameters, or a build123d source be converted to CadQuery mechanically, assisted by
`src/convert_build123d.py`, and validated through `run_cadquery_model.py` like any generated
part. On a re-author choice, the source SHALL be treated like an OpenSCAD source. An OpenSCAD
or FreeCAD source SHALL NOT be transpiled or executed; the file SHALL be used as the
authoritative topology and parameter source and the part re-authored in CadQuery through the
normal part loop. The choice SHALL be recorded in `planning_notes` with the provenance entry.

Rung 1 handling begins once the Sourcing agent's `Rung: 1` is taken for a candidate (see
"Decision ladder classifies the best find"); no kind-based re-derivation precedes it.

#### Scenario: build123d source found and run approved
- **WHEN** rung 1 matches a build123d script and the user chooses to run it
- **THEN** the script is converted to CadQuery with the converter helper and validated via the wrapper before delivery

#### Scenario: CadQuery source found, consent asked first
- **WHEN** rung 1 matches a CadQuery script
- **THEN** the main session asks the user before any `run_cadquery_model.py` call on that script, naming the URL, license and that third-party code will run

#### Scenario: User declines running found code
- **WHEN** the user chooses re-author for a CadQuery or build123d source
- **THEN** no part of the found script is executed, the part is re-authored through the normal part loop using its parameters and topology, and `planning_notes` records the decision

#### Scenario: OpenSCAD source found
- **WHEN** rung 1 matches an OpenSCAD file
- **THEN** the part is re-authored in CadQuery using the .scad's topology and parameter values, and no textual transpilation of the .scad is attempted
