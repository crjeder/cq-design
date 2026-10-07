## ADDED Requirements

### Requirement: A part script is executed at most once per content and print pose per process
`exporters._load_result` SHALL memoize its result for the lifetime of the process, keyed by the script's absolute path, a hash of its bytes, and the `print_rotate` value. A load that must observe execution (a hooked load that wraps CadQuery operations) SHALL skip the lookup (`fresh=True`) and store its result, so later loads reuse it.

#### Scenario: Repeat load of an unchanged script
- **WHEN** `_load_result(script, None)` is called twice in one process and the file is unchanged
- **THEN** the script body executes once and both calls return the same `result`

#### Scenario: Script edited between loads
- **WHEN** the script file's bytes change between two `_load_result` calls
- **THEN** the second call re-executes the script and returns the new `result`

#### Scenario: Different print pose
- **WHEN** `_load_result` is called with two different `print_rotate` values
- **THEN** the script executes once per distinct value

#### Scenario: Hooked load
- **WHEN** a check loads with `fresh=True`
- **THEN** the script executes and its wrapped CadQuery calls are recorded even if a cached result exists, and a later plain load returns that result without executing again

### Requirement: Delivery reuses the shim's loaded result when the pose matches
When `run_cadquery_model.py --deliver` runs without `--print-rotate`, the requested formats SHALL be written from the result the shim subprocess already loaded, without a second import of the script. With `--print-rotate`, delivery SHALL still export the authored-frame result.

#### Scenario: Deliver without rotate
- **WHEN** `--deliver --formats stl,3mf` is given and no `--print-rotate`
- **THEN** the script executes once in total and `stls` and `threemfs` in the JSON output are populated as before

#### Scenario: Deliver with rotate
- **WHEN** `--deliver` is given with `--print-rotate`
- **THEN** the delivered files are the authored-frame geometry, identical to today's output

### Requirement: Edge-treatment and feature-presence share one hooked load
The quality gate SHALL record fillet/chamfer edges and cut/union tool bounding boxes in a single script execution when the part's print rotate is None or identity, and SHALL produce the same findings as running the two checks separately.

#### Scenario: Unrotated part
- **WHEN** the gate runs both stages for a part with no rotate
- **THEN** the script executes once for hook recording and both stages' findings equal their standalone results

#### Scenario: Rotated part
- **WHEN** the part has a non-identity rotate
- **THEN** feature-presence records in the authored frame from its own load, so its findings are unchanged
