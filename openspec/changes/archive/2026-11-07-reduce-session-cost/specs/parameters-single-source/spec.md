## ADDED Requirements

### Requirement: Every dimension is a commented constant in parameters.py

The planner SHALL record every dimension of the design in `parameters.py` as one constant with a comment tagging its origin: `user`, `researched: <source>`, `assumed`, or `design choice` (clearances, gaps, wall allowances). Derived allowances SHALL be constants too, not inline arithmetic in the plan.

#### Scenario: Assumed dimension
- **WHEN** the planner needs a dimension nobody stated (a 1 mm groove clearance)
- **THEN** it is added to `parameters.py` with the tag `design choice` or `assumed`

### Requirement: Plan params may be expressions over those constants

A string value in `BUILD_PLAN.json` `params` SHALL be an expression evaluated by `src/plan_params.py` with numeric literals, names defined in `parameters.py`, `+ - * / //`, unary minus, parentheses, and `min`, `max`, `round`. Any other syntax or an unknown name SHALL be rejected, and no `eval` SHALL be used. Numeric params remain valid.

#### Scenario: Expression resolves
- **WHEN** a param is `"BASKET_RIM_OD_MM + GROOVE_CLEARANCE_MM"` and the constants are 70 and 1
- **THEN** `plan.py validate` accepts it and `Part.param` returns 71

#### Scenario: Unknown name rejected
- **WHEN** a param references `NOPE_MM`
- **THEN** `plan.py validate` fails naming `NOPE_MM`

#### Scenario: Unsafe syntax rejected
- **WHEN** a param is `"__import__('os')"`
- **THEN** it is rejected and nothing is executed

### Requirement: Part scripts read resolved values

`Part.param` SHALL return the resolved numeric value, so part scripts need no change when a param becomes an expression.

#### Scenario: Script unchanged
- **WHEN** a plan param changes from a literal to an expression
- **THEN** the unmodified part script builds the same geometry

### Requirement: A dimension edit rebuilds only affected parts

`plan.py validate` SHALL write `build/params_resolved.json` mapping each part to a hash of its resolved params and SHALL print the parts whose hash changed since the previous successful run. The build rule SHALL rebuild and re-gate only those parts and SHALL re-run the visual audit only for them.

#### Scenario: One constant changed
- **WHEN** only a constant used by part `drawer` is edited
- **THEN** validate reports `drawer` as changed and no other part

#### Scenario: Nothing changed
- **WHEN** no resolved param differs
- **THEN** validate reports no changed parts
