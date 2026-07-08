## ADDED Requirements

### Requirement: Runtime verify-helper failures map to typed errors

The wrapper (`run_cadquery_model.py`) SHALL translate a `RuntimeError` raised by the
runtime boolean-verify helper (silent-boolean, feature-bounds-overflow, or workplane-
drift) into a structured `errors` entry with a specific `type` rather than the generic
`occ_exception` fallback. A silent-boolean failure SHALL use `type: "silent_boolean"`; a
feature-bounds overflow SHALL use `type: "feature_overflow"`; a workplane-origin drift
SHALL use `type: "workplane_drift"`. Each entry SHALL include the feature/workplane
`label` from the helper, a `message` reproducing the helper's detail, and a `hint`
directing the fix (reposition the tool so it overlaps / constrain the feature within the
body / re-anchor the workplane origin). The raw traceback SHALL remain in `stderr`.

#### Scenario: Silent cut raises during construction

- **WHEN** a wrapped `.cut()` produces no change and the helper raises `RuntimeError`
- **THEN** `errors` contains one entry with `type: "silent_boolean"`, the feature
  `label`, and a hint about the tool not overlapping the body; the raw traceback is in
  `stderr`

#### Scenario: Feature overflow raises during construction

- **WHEN** the bounds helper raises `RuntimeError` for a feature extending past the body
- **THEN** `errors` contains one entry with `type: "feature_overflow"`, the feature
  `label`, the per-axis overflow in `message`, and a hint about constraining the feature

#### Scenario: Workplane drift raises during construction

- **WHEN** the workplane check raises `RuntimeError` for an origin that drifted past the
  tolerance
- **THEN** `errors` contains one entry with `type: "workplane_drift"`, the `label`,
  expected vs. actual origin in `message`, and a hint about re-anchoring the workplane

#### Scenario: Non-verify RuntimeError is unaffected

- **WHEN** the script raises a `RuntimeError` that did not originate from the verify
  helper
- **THEN** the wrapper does not classify it as `silent_boolean` or `feature_overflow`
