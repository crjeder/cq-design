# interference-primitive Specification

## Purpose

Provide the model's single, reusable notion of geometric interference between two posed
bodies: an overlap test with a caller-supplied exclusion set that emits the shared
quality-gate issue contract on a violation and degrades gracefully when its collision
backend is unavailable. Consolidates the duplicated overlap machinery in the keep-out
check and the kinematic per-pose collision test into one independently testable core.

## Requirements

### Requirement: A shared primitive tests two posed bodies for overlap against an exclusion set

The system SHALL provide a shared interference primitive that, given a `subject` posed
mesh and a set of `other` posed meshes each identified by name, reports whether the
subject overlaps any `other`, honoring a caller-supplied **exclusion set** of `other`
names that are never tested against the subject.

Overlap SHALL be determined in two stages. The collision backend (trimesh + python-fcl)
SHALL be used as a **broadphase** only: it answers whether two bodies touch at all. When
the broadphase reports contact and the caller supplied a tolerance, the primitive SHALL
measure the interference as the **volume of the boolean intersection** of the two meshes
and count the pair as interfering only when that volume exceeds the caller's tolerance.

The primitive SHALL NOT use the collision backend's reported contact penetration depth as
the interference measure. That value is ill-conditioned for the large near-coplanar
triangles that flat printed faces tessellate into: it is not proportional to the true
overlap and is not monotonic in it, so designed flush contact is indistinguishable from
real interference by depth alone.

Penetration semantics remain a caller choice:
- No tolerance (`None`) -- any broadphase contact counts as interference, with no volume
  measurement performed. This is the keep-out semantics.
- A volume tolerance -- a contact counts only when the measured intersection volume
  exceeds it. This is the kinematic semantics, where designed surface contact at a joint
  must not read as binding.

#### Scenario: Subject overlaps a non-excluded body
- **WHEN** the subject mesh overlaps an `other` mesh whose name is not in the exclusion set, by a volume above the caller's tolerance
- **THEN** the primitive reports that pair as interfering, naming the offending `other`

#### Scenario: Subject overlaps only an excluded body
- **WHEN** the subject mesh overlaps an `other` mesh whose name IS in the exclusion set, and no other body
- **THEN** the primitive reports no interference for that pair

#### Scenario: No overlap
- **WHEN** the subject mesh overlaps none of the non-excluded `other` meshes
- **THEN** the primitive reports no interference

#### Scenario: Flush surface contact is not interference
- **WHEN** two bodies meet in designed face-to-face contact, so the broadphase reports contact but the boolean intersection volume is zero or below the caller's volume tolerance
- **THEN** the primitive reports no interference, regardless of what contact depth the backend reports for that pair

#### Scenario: Any-contact semantics skip volume measurement
- **WHEN** a caller supplies no tolerance and the broadphase reports contact
- **THEN** the primitive reports interference immediately without computing a boolean intersection

#### Scenario: Measured overlap volume is available to the caller
- **WHEN** the primitive determines a pair interferes under a volume tolerance
- **THEN** the measured intersection volume is reported alongside the offending body's name, so the calling stage can include it in its finding

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

The primitive SHALL degrade when its geometry backend cannot be imported: it SHALL
signal `check_skipped` to the caller rather than raise, so each consuming stage emits a
single `severity: "warning"`, `type: "check_skipped"` issue and performs no comparison,
matching the existing degrade behavior of the keep-out, kinematic, and plate-clearance
checks.

The backend comprises trimesh, python-fcl, and the boolean engine used for volume
measurement. All three SHALL be treated as one unit: if any is missing, the primitive
signals `check_skipped`. The primitive SHALL NOT fall back to a second, weaker
interference measure when the boolean engine is absent, because two measures with
different sensitivity would make findings incomparable between runs and would silently
reintroduce the depth-based false positives this design removes.

#### Scenario: Backend unavailable
- **WHEN** the collision backend cannot be imported
- **THEN** the primitive performs no comparison and signals `check_skipped` without raising

#### Scenario: Boolean engine unavailable
- **WHEN** trimesh and python-fcl import but the boolean engine does not
- **THEN** the primitive signals `check_skipped` and does not fall back to depth-based or any other substitute measure

### Requirement: Existing consumers preserve their behavior when refactored onto the primitive

The keep-out validation stage and the kinematic per-pose collision test SHALL call the
shared primitive rather than inlining overlap machinery. The kinematic stage's
`required_range` scalar bound check and its sweep, trajectory, and swept-subtree
rigid-carry SHALL remain in the kinematic stage and SHALL NOT be absorbed into the
primitive.

Keep-out behavior SHALL be unchanged by the move to volume-based measurement: it passes
no tolerance, so it keeps any-contact semantics and produces the same findings as before.
Kinematic collision outcomes MAY change, and are intended to: a pose whose contact was
previously reported as binding on the strength of an ill-conditioned depth value, but
whose true intersection volume is within tolerance, SHALL no longer be reported as
binding. This is the defect being fixed, not a regression.

#### Scenario: Keep-out output unchanged after refactor
- **WHEN** a model that previously produced a given set of `keep_out_violation` findings (or none) is checked after the refactor
- **THEN** the keep-out stage produces the same set of findings

#### Scenario: Genuine kinematic interference is still reported
- **WHEN** a swept pose drives one union into another by an intersection volume above the tolerance
- **THEN** the kinematic stage still reports a collision naming the same offending union as before

#### Scenario: Depth-only false positive is no longer reported
- **WHEN** a swept pose brings two unions into flush contact that the previous depth-thresholded implementation reported as a collision, and the true intersection volume is within tolerance
- **THEN** the kinematic stage reports no collision for that pose
