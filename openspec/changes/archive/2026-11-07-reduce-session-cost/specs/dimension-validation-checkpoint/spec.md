## ADDED Requirements

### Requirement: The exit checkpoint includes the concept sketch

The Phase 1 exit checkpoint SHALL present the concept sketch (see `concept-sketch`) together with the dimension table. Approval SHALL cover both, and the `dimensions_approved` milestone SHALL be recorded only after both are approved.

#### Scenario: Both approved
- **WHEN** the user approves the dimensions and the sketch
- **THEN** `parameters.py` is written and `dimensions_approved` is journaled

#### Scenario: Sketch rejected
- **WHEN** the user rejects the sketch
- **THEN** no `dimensions_approved` milestone is written until a revised sketch is approved
