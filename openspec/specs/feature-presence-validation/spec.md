# feature-presence-validation Specification

## Purpose

Deterministically confirm that every plan-declared interface feature which specifies a
structured position is actually realized at that position in the constructed part, as a
build-failing backstop beneath the visual per-feature review. Scoped to features emitted
through construction paths the check can attribute a position to; other features degrade to
a skip rather than a false failure.

## Requirements

### Requirement: The gate asserts every structured-position interface feature is present

The quality gate SHALL, for each part, verify that every `interfaces[]` entry declaring a
structured `position_mm` is realized by a feature whose authored-frame center lies within a
position tolerance of the declared position. When no built feature matches a declared
position, the gate SHALL emit a blocking finding; the check SHALL determine built features
at construction time (by hooking the placement-bearing operations and re-running the part
script), NOT by reverse-engineering the exported mesh.

#### Scenario: Declared feature present at its position
- **WHEN** an interface entry declares `position_mm` and a built feature's center lies within the position tolerance of it
- **THEN** the gate reports no feature-presence issue for that entry

#### Scenario: Declared feature absent
- **WHEN** an interface entry declares `position_mm` and no built feature's center lies within the position tolerance of it
- **THEN** the gate emits a `feature_absent` error naming the part, the interface `type`, and the declared position

#### Scenario: Interface without a declared position is not asserted
- **WHEN** an interface entry declares no structured `position_mm`
- **THEN** the gate performs no presence assertion for that entry and emits no issue for it

### Requirement: A present-but-drifted feature is an advisory finding

The gate SHALL emit a `feature_drift` warning (not a `feature_absent` error) when a built
feature matches a declared interface position within the generous position tolerance but
its center or size differs beyond the tighter drift tolerance -- the feature exists, but
not exactly as declared.

#### Scenario: Feature present but off-position
- **WHEN** a built feature is the nearest match to a declared position within the position tolerance, but its center differs beyond the drift tolerance
- **THEN** the gate emits a `feature_drift` warning, not a `feature_absent` error

#### Scenario: Feature present but wrong size
- **WHEN** a built feature matches a declared position within tolerance but its size differs beyond the size tolerance from a declared size
- **THEN** the gate emits a `feature_drift` warning naming the expected and actual size

### Requirement: Only assertable interface types are checked; others are skipped

The check SHALL assert only interface `type`s emitted through a hooked construction path (an
allowlist covering the interface-emitting blocks applied via `.cut` / `.union`). An entry
whose `type` is outside the allowlist, or a part whose script cannot be re-run with the
hooks, SHALL be reported as `check_skipped`, never as `feature_absent`, so a feature built
by an un-hooked path never produces a false failure.

#### Scenario: Non-assertable interface type
- **WHEN** an interface entry declares a `position_mm` but its `type` is outside the assertable allowlist
- **THEN** the gate emits a `check_skipped` warning for that entry and no `feature_absent` error

#### Scenario: Part script cannot be re-run
- **WHEN** the part script cannot be re-run with the hooks installed (e.g. CadQuery unavailable)
- **THEN** the stage emits a single `check_skipped` warning for that part and performs no presence assertion

### Requirement: Findings use the structured issue contract

Feature-presence findings SHALL be issue objects matching the quality-gate contract: each
SHALL have `source`, `severity` (`error` for `feature_absent`, `warning` for
`feature_drift` and `check_skipped`), `type`, a human-readable `message` naming the part /
interface / position, and a `hint` directing the fix at the missing or misplaced feature. A
`feature_absent` finding SHALL block a clean pass; `feature_drift` and `check_skipped` SHALL
NOT.

#### Scenario: Issue shape
- **WHEN** a feature-presence finding is emitted
- **THEN** it contains `source`, `severity`, `type`, `message`, and `hint` keys and is consumable by the fix-prompt renderer without modification

#### Scenario: Absent blocks, drift does not
- **WHEN** a `feature_absent` error and a `feature_drift` warning are both emitted for a model
- **THEN** the `feature_absent` error blocks a clean pass and the `feature_drift` warning does not
