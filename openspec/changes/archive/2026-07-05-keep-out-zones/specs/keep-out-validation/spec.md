## ADDED Requirements

### Requirement: The gate checks every union against every declared keep-out zone

The quality gate SHALL, for every declared keep-out zone in the model, test its assembled-frame
geometry for intersection against every union's assembled-frame geometry, **excluding the zone's own
declaring part's other real unions**. Any intersecting union SHALL cause the gate to reject the
design rather than pass silently.

#### Scenario: Foreign union intrudes on a zone
- **WHEN** a union belonging to a different part than the zone's declaring part overlaps a declared
  keep-out zone
- **THEN** the gate emits a `keep_out_violation` error naming the offending union and the zone

#### Scenario: No union intrudes
- **WHEN** no union's geometry overlaps any declared keep-out zone
- **THEN** the gate contributes no keep-out issues

#### Scenario: Declaring part's own real union is excluded
- **WHEN** a keep-out zone is anchored flush against its own declaring part's real union (e.g. a
  screwdriver-clearance zone starting at the boss it protects)
- **THEN** that declaring part's own real union is not checked against its own zone, and no
  false-positive violation is reported for that pair

#### Scenario: A different part's zone still checks against the first part's union
- **WHEN** part A declares a keep-out zone and part B's union overlaps it
- **THEN** the violation is reported (the exclusion only applies to the zone's own declaring part,
  not to other parts)

---

### Requirement: Keep-out violations use the structured issue contract and block a clean pass

Keep-out findings SHALL be emitted as issue objects matching the quality gate contract: each issue
SHALL have `source: "geometry"`, `severity: "error"`, `type: "keep_out_violation"`, a human-readable
`message` naming both the offending union and the violated zone (by its declaring part and zone
name), and a `hint` directing that the offending geometry -- not the zone -- be redesigned. A
`keep_out_violation` SHALL block a clean pass.

#### Scenario: Issue shape
- **WHEN** a `keep_out_violation` issue is emitted
- **THEN** it contains `source`, `severity`, `type`, `message`, and `hint` keys and is consumable by
  the fix-prompt renderer without modification

#### Scenario: Error blocks a clean pass
- **WHEN** a `keep_out_violation` issue is emitted
- **THEN** the gate does not report a clean pass and the issue surfaces in the fix prompt

#### Scenario: Hint points at the offending geometry, not the zone
- **WHEN** a `keep_out_violation` issue is emitted
- **THEN** its `hint` directs the fix at the offending union's geometry, since the zone itself is
  never redesigned

---

### Requirement: Missing geometry dependencies degrade to a warning

The keep-out check SHALL degrade to a warning when its geometry dependencies (trimesh and its
collision backend) cannot be imported: it SHALL emit a single issue with `severity: "warning"` and
`type: "check_skipped"` and SHALL NOT raise, matching the kinematic check's and plate-clearance
check's degrade behavior.

#### Scenario: Backend unavailable
- **WHEN** trimesh or the collision backend cannot be imported and the model declares at least one
  keep-out zone
- **THEN** the stage emits one `check_skipped` warning and performs no comparison, without raising

#### Scenario: No zones declared, dependencies missing
- **WHEN** the model declares no keep-out zones at all
- **THEN** the stage performs no comparison and emits no issue, regardless of whether the geometry
  backend is available
