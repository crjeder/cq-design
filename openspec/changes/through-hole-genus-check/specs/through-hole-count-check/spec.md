## ADDED Requirements

### Requirement: Interfaces declare their through openings

`BUILD_PLAN.json` `parts[].interfaces[]` items SHALL accept an optional integer
`through_count` (minimum 0): the number of openings closed by material all round that the
interface cuts through the part. `plan.py validate` SHALL reject a negative or non-integer
value.

#### Scenario: Blind tapped hole
- **WHEN** an interface declares `"through_count": 0`
- **THEN** the plan validates and the interface contributes 0 to the part's planned b1

#### Scenario: Invalid value
- **WHEN** an interface declares `"through_count": -1`
- **THEN** `plan.py validate` reports a schema error for that interface

### Requirement: Planner decides through vs blind from the drawing

The planning prompt SHALL instruct the planner that a hole is through only when a section view
shows it through or its callout says THRU; a tapped or depth-dimensioned callout without THRU
is blind (`through_count: 0`). Every hole, slot and cutout interface SHALL state
`through_count`, counting only openings closed by material all round (an edge notch is 0).

#### Scenario: Tapped callout
- **WHEN** a drawing calls out an M4 tapped hole without THRU
- **THEN** the planned interface has `through_count: 0`

### Requirement: Gate compares built b1 with the planned total

When at least one interface on a part declares `through_count`, the quality gate SHALL compute
the built b1 as the sum over the part's non-sacrificial union meshes of `c - chi/2` (chi the
mesh's Euler characteristic, c its number of connected surface components), and SHALL emit a
blocking error of type `through_hole_count_mismatch` with `planned_b1` and `built_b1` when it
differs from the sum of `through_count` over the part's interfaces. The check SHALL be skipped
when any of those meshes is not watertight, and when no interface on the part declares
`through_count`.

#### Scenario: Counts match
- **WHEN** a plate plans 4 interfaces with `through_count: 1` and the built mesh has genus 4
- **THEN** the gate reports no `through_hole_count_mismatch`

#### Scenario: Blind hole built through
- **WHEN** a part plans 2 through holes and 2 blind holes, and all 4 are cut through
- **THEN** the gate reports `through_hole_count_mismatch` with `planned_b1: 2`, `built_b1: 4`
  and severity `error`

#### Scenario: Legacy plan
- **WHEN** no interface on the part declares `through_count`
- **THEN** the gate runs no b1 check and reports no `through_hole_count_mismatch`

#### Scenario: Internal void
- **WHEN** a part has no through holes and a sealed internal cavity, with all interfaces at
  `through_count: 0`
- **THEN** the built b1 is 0 and no mismatch is reported
