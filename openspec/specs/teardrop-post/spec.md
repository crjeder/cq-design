# Teardrop Post

## Purpose

Defines requirements for the `teardrop_post` block: a self-supporting horizontal cylindrical protrusion (peg/pin/boss) whose underside is truncated with inclined faces so it prints without support, sharing a drop-profile helper with `teardrop_bore`.

## Requirements

### Requirement: Teardrop post block produces a self-supporting horizontal peg

The system SHALL provide a `teardrop_post` function in `blocks/connectors.py` that
returns a `cq.Workplane` solid representing a HORIZONTAL cylindrical protrusion
(peg, pin, or boss) suitable for unioning onto a part. The solid's upper half SHALL
be a circular arc of radius `d/2`; its lower half SHALL be replaced by two flat
faces meeting a narrow flat bottom, so the underside self-supports when printed in
the modeled orientation.

The function signature SHALL be `teardrop_post(d, length, angle=45, flat=1.2)` where
`d` is the cylinder diameter in mm, `length` is the protrusion length along the axis
in mm, `angle` is the underside face angle from horizontal in degrees, and `flat` is
the width of the flat bottom in mm.

#### Scenario: Returns a valid solid
- **WHEN** `teardrop_post(d=8.0, length=6.0)` is called
- **THEN** it returns a `cq.Workplane` containing a single watertight solid

#### Scenario: Unioning onto a wall yields a watertight body
- **WHEN** the returned post is unioned onto a box face with `.union()`
- **THEN** the resulting body is watertight

### Requirement: Lower profile is two 45-degree faces and a flat bottom

The cross-section SHALL replace the lower half of the circle with two straight
faces running from the equator points `(+/-d/2, 0)` at `angle` from horizontal,
descending toward a horizontal flat bottom of width `flat` (this construction
mirrors `teardrop_bore`'s peak, so the shared profile keeps `teardrop_bore`
unchanged). The upper half SHALL remain a circular arc of radius `d/2`. No part of
the profile below the horizontal centerline SHALL be a circular arc.

#### Scenario: Default face angle is the overhang limit
- **WHEN** `teardrop_post(d, length)` is called without an `angle` argument
- **THEN** the underside faces are at 45 degrees from horizontal (the printable overhang limit)

#### Scenario: Underside faces stay within the overhang limit
- **WHEN** `teardrop_post(d, length, angle=45)` is called
- **THEN** every face of the solid below the horizontal centerline is at or below 45 degrees of overhang relative to the build direction

#### Scenario: Flat bottom is at the minimum Z
- **WHEN** the post is built in its default orientation
- **THEN** the flat bottom is at the minimum Z of the cross-section, so the underside self-supports when printed in the modeled orientation

### Requirement: Small features are handled by advisory, never by failure

The `teardrop_post` block SHALL always return a buildable solid. When the requested
`flat` would not leave valid inclined faces (when `flat` is not strictly less than
`d`), the block SHALL clamp the effective flat width (to `d/2`) so the faces remain
valid. When `d` is below the diameter at which the self-supporting treatment is
useful (a module-level threshold, default 3.0 mm), the block SHALL emit a
`warnings.warn` advisory but SHALL still build. The block SHALL NOT raise on small
diameters.

#### Scenario: Tiny diameter builds with an advisory
- **WHEN** `teardrop_post(d=2.0, length=4.0)` is called
- **THEN** it returns a valid watertight solid AND emits a `warnings.warn` advisory

#### Scenario: Oversized flat is clamped, not fatal
- **WHEN** `teardrop_post(d=4.0, length=4.0, flat=5.0)` is called with a flat at least as wide as `d`
- **THEN** the effective flat is clamped so inclined faces still exist AND a valid watertight solid is returned

### Requirement: Block is registered in the inventory and exported

The system SHALL register `teardrop_post` in `blocks/inventory.json` with a
descriptor including `name`, `module` (`blocks.connectors`), `function`, `use`,
`params`, `dimensions`, and `interfaces`, and SHALL re-export it from the `blocks`
package `__init__`. The descriptor SHALL declare one interface of type `axis`
oriented along the post. The `use` string SHALL state the minimum useful diameter
guidance and SHALL redirect functional peg/socket pairs to a 45-degree-rotated cube.

#### Scenario: Inventory lookup
- **WHEN** the orchestrator looks up `"teardrop_post"` in `blocks/inventory.json`
- **THEN** it receives the full descriptor including params and an `axis` interface

#### Scenario: Use string carries minimum-diameter and mating guidance
- **WHEN** the `teardrop_post` descriptor `use` string is read
- **THEN** it states the minimum useful diameter and directs functional peg/socket pairs to a 45-degree-rotated cube

#### Scenario: Import from the blocks package
- **WHEN** a model script runs `from blocks import teardrop_post`
- **THEN** the import succeeds and the function is callable

### Requirement: Shared drop profile helper preserves teardrop_bore behavior

The system SHALL factor the drop-shaped cross-section into a `_drop_profile`
helper in `blocks/connectors.py` parameterized by radius, angle, and apex direction.
`teardrop_bore` SHALL consume this helper with the apex pointing up and SHALL
produce geometry identical to its prior behavior. `teardrop_post` SHALL consume the
helper with the apex pointing down plus flat truncation.

#### Scenario: teardrop_bore output unchanged
- **WHEN** `teardrop_bore(d=8.0, depth=4.0)` is called after the refactor
- **THEN** the circular portion has diameter 8.0 mm, the extrusion length along the bore axis equals `4.0 + _EPS`, and the upper profile is a peak (no arc above the horizontal centerline)
