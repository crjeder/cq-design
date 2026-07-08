# interference-primitive Specification

## Purpose

Provide the model's single, reusable notion of geometric interference between two posed
bodies: an overlap test with a caller-supplied exclusion set that emits the shared
quality-gate issue contract on a violation and degrades gracefully when its collision
backend is unavailable. Consolidates the duplicated overlap machinery in the keep-out
check and the kinematic per-pose collision test into one independently testable core.

## ADDED Requirements

### Requirement: A shared primitive tests two posed bodies for overlap against an exclusion set

The system SHALL provide a shared interference primitive that, given a `subject` posed
mesh and a set of `other` posed meshes each identified by name, reports whether the
subject overlaps any `other`, honoring a caller-supplied **exclusion set** of `other`
names that are never tested against the subject. Overlap SHALL be determined with the
same trimesh + collision-backend tooling the keep-out and kinematic stages use today.

#### Scenario: Subject overlaps a non-excluded body
- **WHEN** the subject mesh overlaps an `other` mesh whose name is not in the exclusion set
- **THEN** the primitive reports that pair as interfering, naming the offending `other`

#### Scenario: Subject overlaps only an excluded body
- **WHEN** the subject mesh overlaps an `other` mesh whose name IS in the exclusion set, and no other body
- **THEN** the primitive reports no interference for that pair

#### Scenario: No overlap
- **WHEN** the subject mesh overlaps none of the non-excluded `other` meshes
- **THEN** the primitive reports no interference

### Requirement: Interference findings use the structured issue contract

When the primitive is used to produce gate findings, each finding SHALL be an issue
object matching the quality-gate contract: `source`, `severity`, `type`, a
human-readable `message` naming the interfering bodies, and a `hint`. The `type`,
`severity`, and `hint` wording SHALL be supplied by the calling stage (e.g.
`keep_out_violation`) so the primitive stays agnostic to which check invoked it, while
the issue shape is uniform and consumable by the fix-prompt renderer without
modification.

#### Scenario: Finding shape
- **WHEN** the primitive yields an interference finding for a caller
- **THEN** the finding contains `source`, `severity`, `type`, `message`, and `hint` keys, with the caller-supplied `type`/`severity`/`hint` and a `message` naming both interfering bodies

### Requirement: The primitive degrades to a warning when its backend is unavailable

The primitive SHALL degrade when its collision backend (trimesh and python-fcl) cannot
be imported: it SHALL signal `check_skipped` to the caller rather than raise, so each
consuming stage emits a single `severity: "warning"`, `type: "check_skipped"` issue and
performs no comparison, matching the existing degrade behavior of the keep-out,
kinematic, and plate-clearance checks.

#### Scenario: Backend unavailable
- **WHEN** the collision backend cannot be imported
- **THEN** the primitive performs no comparison and signals `check_skipped` without raising

### Requirement: Existing consumers preserve their behavior when refactored onto the primitive

The keep-out validation stage and the kinematic per-pose collision test SHALL produce
byte-equivalent findings (same `type`, same offending-body naming, same pass/fail
outcomes, same degrade behavior) after being refactored to call the shared primitive as
they did with their inlined overlap code. The kinematic stage's `required_range`
scalar bound check and its sweep, trajectory, and swept-subtree rigid-carry SHALL remain
in the kinematic stage and SHALL NOT be absorbed into the primitive.

#### Scenario: Keep-out output unchanged after refactor
- **WHEN** a model that previously produced a given set of `keep_out_violation` findings (or none) is checked after the refactor
- **THEN** the keep-out stage produces the same set of findings

#### Scenario: Kinematic collision output unchanged after refactor
- **WHEN** a model that previously produced a given set of kinematic collision findings (or none) is swept after the refactor
- **THEN** the kinematic stage produces the same collision findings, and its range check and sweep are unchanged
