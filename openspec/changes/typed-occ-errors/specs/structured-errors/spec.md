## MODIFIED Requirements

### Requirement: Known OCC exception classes map to actionable hints
The wrapper SHALL maintain a translation table mapping known OCC exception class
names to a distinct structured-error `type` and a specific, actionable hint. At
minimum the following SHALL be covered:

| OCC class | `type` | hint |
|-----------|--------|------|
| `Standard_ConstructionError` | `construction_error` | "geometry construction failed -- check that boolean bodies overlap and no faces are coincident" |
| `BRep_API` (command not done) | `command_not_done` | "boolean operation failed -- ensure inner body extends at least 0.01 mm past outer boundary" |
| `StdFail_NotDone` | `fillet_failure` | "operation left incomplete -- fillet radius may exceed adjacent face dimension; reduce radius" |
| `Standard_NullObject` | `null_object` | "referenced a shape that does not exist -- check selector strings and workplane offsets" |
| `Standard_OutOfRange` | `index_out_of_range` | "index out of range -- check pushPoints list or loop bounds" |
| `Standard_TypeMismatch` | `type_mismatch` | "wrong shape type for this operation -- verify the workplane and selector are targeting the correct geometry" |

An OCC exception class not in this table SHALL still be reported with
`type: "occ_exception"` and the generic fallback hint. Every entry, mapped or
not, SHALL carry the raw exception class name in `occ_class`.

#### Scenario: Known OCC exception
- **WHEN** the script raises `StdFail_NotDone`
- **THEN** `errors` contains one entry with `type: "fillet_failure"`,
  `occ_class: "StdFail_NotDone"`, and the specific hint for that class

#### Scenario: Command-not-done boolean failure
- **WHEN** the script raises `BRep_API`
- **THEN** `errors` contains one entry with `type: "command_not_done"` and the
  boolean-overlap hint

#### Scenario: Unknown OCC exception
- **WHEN** the script raises an OCC exception not in the translation table
- **THEN** `errors` contains `type: "occ_exception"` with `occ_class` set to
  the raw class name, its message, and the generic hint "check CadQuery
  documentation for this exception class"
