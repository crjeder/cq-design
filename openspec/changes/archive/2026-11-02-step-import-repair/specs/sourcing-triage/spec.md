## MODIFIED Requirements

### Requirement: BREP import is scoped as a dumb solid
At rung 2, a found STEP/BREP file SHALL be imported via `blocks.import_solid` (the checked import, which may repair an invalid file), and an IGES file via `cq.importers`. The import SHALL be used only as a mating reference or a base for boolean modification. The result SHALL be described to the user as non-reparametrizable. A `step_unrepairable` error SHALL drop the candidate to the next rung.

Rung 2 handling begins once the Sourcing agent's `Rung: 2` is taken for a candidate; no
kind-based re-derivation precedes it.

#### Scenario: STEP file used as mating reference
- **WHEN** rung 2 matches a STEP file for a commercial part the model must mate with
- **THEN** the solid is imported with `blocks.import_solid` and used as reference or boolean input, and the delivery notes state the imported body is a dumb solid

#### Scenario: Unrepairable vendor file
- **WHEN** `blocks.import_solid` raises `step_unrepairable` for the rung-2 file
- **THEN** the candidate is not used at rung 2 and triage continues with the next rung
