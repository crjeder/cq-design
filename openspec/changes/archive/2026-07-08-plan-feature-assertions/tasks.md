## 1. Tighten the interfaces[] schema (prerequisite)

- [x] 1.1 In `src/build_plan_schema.json`, replace the interface entry's `additionalProperties: true` with a defined shape: required `type`; optional structured `wall` (enum of the six faces), `position_mm` (array of 3 numbers), `diameter_mm` (number) and `size_mm` (array of 2 numbers); keep existing free-form fields (`description`, `connector`, `clearance_mm`) allowed.
- [x] 1.2 Confirm existing plans still validate: `type`-only interfaces, empty interfaces arrays, and the `test_plan_validate.py` fixtures. Add schema tests for a well-formed structured placement and a rejected malformed one (`position_mm` not length-3, size wrong type).
- [x] 1.3 Update `prompts/planning.md` (and any interface guidance in `reference/`) to emit structured `position_mm` + size when the position is known, noting it enables the deterministic feature-presence check.

## 2. Construction-time feature recorder

- [x] 2.1 New `src/feature_presence_check.py`: install hooks on the positioned-tool booleans (`cq.Workplane.cut`, `.union`), re-run the part script via `exporters._load_result` (the `edge_treatment_check` pattern), and record each call's tool-argument authored-frame bbox center + extents. (Hole family `.hole`/`.cboreHole`/`.cutBlind`/`.cutThruAll` deferred -- see design D1; block bores are covered via `.union`.)
- [x] 2.2 Attribute each recorded feature to its union by bbox (reuse the `edge_treatment_check` `_BBOX_TOL_MM` attribution approach); no print-orientation rotation (positions are authored-frame, matching `position_mm`).
- [x] 2.3 Define module-level tolerance constants: `_POS_TOL_MM` (generous match radius), `_DRIFT_TOL_MM` (tight center drift), and a size tolerance.

## 3. Match declared interfaces against recorded features

- [x] 3.1 For each part interface entry that declares `position_mm` and whose `type` is in the assertable allowlist (`port_cutout`, `cable_slot`, `vent_grid`, `screw_boss`, `pcb_standoff`), find the nearest recorded feature within `_POS_TOL_MM`.
- [x] 3.2 Emit `feature_absent` (error) when none matches; `feature_drift` (warning) when the nearest match is beyond `_DRIFT_TOL_MM` in center or beyond the size tolerance; pass otherwise.
- [x] 3.3 Emit `check_skipped` (warning) for a declared-position interface whose `type` is outside the allowlist, and one `check_skipped` per part whose script cannot be re-run (e.g. CadQuery unavailable). Never emit `feature_absent` in those cases.
- [x] 3.4 All findings use `make_issue` with the shared `{source, severity, type, message, hint}` contract, naming part / interface `type` / declared position; `feature_absent` blocks a clean pass, the warnings do not.

## 4. Wire into the gate

- [x] 4.1 Wire `feature_presence_check` into `src/quality_gate.py` as a once-outside-the-fix-loop stage (same wiring point as `edge_treatment_check`), passing the plan and each part script.
- [x] 4.2 Update `CLAUDE.md` Core Scripts table with `src/feature_presence_check.py`; note the visual per-feature question in `reference/Visual Review Checklist.md` remains the perceptual cross-check beneath this deterministic backstop.

## 5. Tests

- [x] 5.1 New `tests/test_feature_presence_check.py`: a part with a `port_cutout` present at the declared position passes; the same declared position with the cut removed yields one `feature_absent` error; a cut placed off-position yields a `feature_drift` warning.
- [x] 5.2 A declared-position interface with a non-allowlisted `type` yields `check_skipped`, not `feature_absent`.
- [x] 5.3 An interface entry with only a `type` (no `position_mm`) yields no finding.
- [x] 5.4 `openspec validate plan-feature-assertions --strict`.
