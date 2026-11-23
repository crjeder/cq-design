## MODIFIED Requirements

### Requirement: Gate compares built b1 with the planned total

The quality gate SHALL run the b1 check on a part when the plan's `design_intent` is `"cad"`,
or when at least one interface on the part declares `through_count`. The built b1 SHALL be
the sum over the part's non-sacrificial union meshes of `c - chi/2` (chi the mesh's Euler
characteristic, c its number of connected surface components). The planned b1 SHALL be the
part's value in the latest valid `phase2/plan_approved` journal line's `b1=` record when one
exists, and otherwise the sum of `through_count` over the part's interfaces, with a missing
`through_count` counted as 0. When the built b1 differs from the planned b1, the gate SHALL
emit a blocking error of type `through_hole_count_mismatch` with `planned_b1` and `built_b1`.
When the live plan's sum differs from the approved value, the issue SHALL also carry
`approved_b1` and `plan_b1`, and its message SHALL state that the plan changed after
approval. The check SHALL be skipped when any of the meshes is not watertight, and, under
print intent, when no interface on the part declares `through_count`.

#### Scenario: Counts match
- **WHEN** a plate plans 4 interfaces with `through_count: 1` and the built mesh has genus 4
- **THEN** the gate reports no `through_hole_count_mismatch`

#### Scenario: Blind hole built through
- **WHEN** a part plans 2 through holes and 2 blind holes, and all 4 are cut through
- **THEN** the gate reports `through_hole_count_mismatch` with `planned_b1: 2`, `built_b1: 4`
  and severity `error`

#### Scenario: Legacy plan
- **WHEN** the plan's `design_intent` is `"print"` and no interface on the part declares
  `through_count`
- **THEN** the gate runs no b1 check and reports no `through_hole_count_mismatch`

#### Scenario: Internal void
- **WHEN** a part has no through holes and a sealed internal cavity, with all interfaces at
  `through_count: 0`
- **THEN** the built b1 is 0 and no mismatch is reported

#### Scenario: CAD intent with no declared interfaces
- **WHEN** the plan's `design_intent` is `"cad"`, the part has `interfaces: []`, and the
  built mesh has genus 4
- **THEN** the gate reports `through_hole_count_mismatch` with `planned_b1: 0` and
  `built_b1: 4`

#### Scenario: Plan lowered after approval
- **WHEN** the latest valid `plan_approved` line records `b1=elbow:9`, the live plan's
  `through_count` sum for `elbow` is 6, and the built mesh has genus 6
- **THEN** the gate reports `through_hole_count_mismatch` with `planned_b1: 9`,
  `built_b1: 6`, `approved_b1: 9` and `plan_b1: 6`

#### Scenario: Standalone gate run
- **WHEN** no `build/journal.md` exists next to the plan
- **THEN** the planned b1 is the live plan's sum
