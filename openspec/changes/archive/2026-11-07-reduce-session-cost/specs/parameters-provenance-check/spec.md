## ADDED Requirements

### Requirement: Plan literals that duplicate a parameters.py constant are flagged

The gate SHALL emit an advisory finding when a numeric value in a plan's `params` equals the value of a `parameters.py` constant (values 0 and 1 excluded), naming the param and the constant. It SHALL NOT fail the gate. It SHALL also flag a `parameters.py` constant without an origin tag.

#### Scenario: Duplicate literal
- **WHEN** a plan param is `70` and `BASKET_RIM_OD_MM = 70` exists
- **THEN** an advisory names both

#### Scenario: Expression param
- **WHEN** the param is the expression `"BASKET_RIM_OD_MM"`
- **THEN** no duplicate finding is emitted

#### Scenario: Missing origin tag
- **WHEN** a constant carries no `user`, `researched`, `assumed` or `design choice` tag
- **THEN** an advisory names the constant
