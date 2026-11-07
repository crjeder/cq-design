# assembly-interference-validation Specification

## Purpose

Detects unintended solid overlap between unions of the assembled model at rest pose, so a design whose parts physically collide is rejected before delivery.

## Requirements

### Requirement: The gate checks every pair of unions for rest-pose overlap
The quality gate SHALL, once per run outside the fix loop, test every pair of unions' assembly-pose geometry (the `write_assembly.py` STLs) for intersection, using a broadphase pass first and measuring the boolean intersection volume only for touching pairs. A pair whose intersection volume exceeds 0.1 mm^3 SHALL cause the gate to reject the design. Keep-out zone STLs SHALL NOT be treated as unions.

#### Scenario: Lid sunk into its box with no joint declared
- **WHEN** two unions on different plates overlap by more than 0.1 mm^3 and no joint exempts them
- **THEN** the gate emits one `assembly_interference` error naming both unions and the measured `overlap_mm3`

#### Scenario: Flush contact passes
- **WHEN** two unions touch face to face with measured intersection volume at or below 0.1 mm^3
- **THEN** the gate emits no `assembly_interference` issue for that pair

#### Scenario: Disjoint model
- **WHEN** no two unions touch
- **THEN** the stage contributes no issues and no boolean is computed

### Requirement: Co-plated pairs are left to plate-clearance validation
A pair of unions on the same plate SHALL be skipped by this stage, because `plate-clearance-validation` already rejects them at or below one layer height of gap.

#### Scenario: Co-plated overlap is reported once
- **WHEN** two co-plated unions overlap
- **THEN** only the plate-clearance stage reports the pair

### Requirement: Press-fit joint members are exempt
A pair of unions that are the two members of one `joints` entry whose declared `params.clearance` is negative SHALL be exempt. Every union of a `copy_of` part whose source part is a member part SHALL inherit the exemption. A joint with no declared `clearance`, or a zero or positive one, SHALL NOT exempt its members.

#### Scenario: Press-fit joint overlap passes
- **WHEN** a joint declaring a negative `params.clearance` joins two unions that overlap
- **THEN** no `assembly_interference` issue is emitted for that pair

#### Scenario: Gap-fit joint members overlap
- **WHEN** a joint with positive clearance joins two unions that overlap by more than 0.1 mm^3
- **THEN** the gate emits an `assembly_interference` error

#### Scenario: Mirrored copy inherits exemption
- **WHEN** a part declared `copy_of` a press-fit member part overlaps the other member's union
- **THEN** that pair is exempt

### Requirement: Stale or unavailable inputs degrade like the other whole-model checks
A union whose source script changed since export SHALL produce a `stale_artifact` error and be excluded from the pair test. A missing union STL or an unavailable geometry backend SHALL produce a `check_skipped` warning instead of an error.

#### Scenario: Backend missing
- **WHEN** trimesh, python-fcl or manifold3d is not importable
- **THEN** the stage returns a single `check_skipped` warning
