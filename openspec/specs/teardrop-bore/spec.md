# Teardrop Bore

## Purpose

Defines requirements for the `teardrop_bore` block: a self-supporting horizontal hole cutter whose cross-section replaces the upper half of a circular bore with a printable peak, so horizontal bores can be cut without support material.

## Requirements

### Requirement: Teardrop bore block produces a self-supporting horizontal hole cutter

The system SHALL provide a `teardrop_bore` function in `blocks/connectors.py` that returns a `cq.Workplane` solid suitable for subtraction from a wall, producing a drop-shaped (teardrop) horizontal bore. The cutter cross-section SHALL consist of a lower circular portion of diameter `d` and an upper peak (`^`, two flat faces meeting at an apex) replacing the upper half of the circle, so that the bore self-supports when printed with the peak pointing up.

The function signature SHALL be `teardrop_bore(d, depth, angle=45)` where `d` is the bore diameter in mm, `depth` is the wall thickness to cut through in mm, and `angle` is the roof face angle from horizontal in degrees.

#### Scenario: Returns a valid cutter solid
- **WHEN** `teardrop_bore(d=8.0, depth=4.0)` is called
- **THEN** it returns a `cq.Workplane` containing a single watertight solid

#### Scenario: Subtracting from a wall yields a watertight body
- **WHEN** the returned cutter is subtracted from a box at least `d` tall and at least `depth` thick along the bore axis
- **THEN** the resulting body is watertight with no coincident faces on the bore exit surface

### Requirement: Upper profile is a peak, not an arc

The cross-section of the cutter SHALL replace the upper half of the circle with two straight roof faces that meet at a single apex on the vertical centerline above the bore. The lower half SHALL remain a circular arc of radius `d/2`. No part of the profile above the horizontal centerline SHALL be a circular arc.

#### Scenario: Default peak angle is the overhang limit
- **WHEN** `teardrop_bore(d, depth)` is called without an `angle` argument
- **THEN** the roof faces are at 45 degrees from horizontal (the printable overhang limit)

#### Scenario: Roof faces stay within the overhang limit
- **WHEN** `teardrop_bore(d, depth, angle=45)` is called
- **THEN** every face of the cutter above the horizontal centerline is at or below 45 degrees of overhang relative to the build direction

#### Scenario: Apex points up
- **WHEN** the cutter is built in its default orientation
- **THEN** the apex of the peak is at the maximum Z of the cross-section, so the bore roof self-supports when printed in the modeled orientation

### Requirement: Exit face is overcut by epsilon

The `teardrop_bore` cutter SHALL extrude along the bore axis by `depth + _EPS`, where `_EPS` is the module-level constant defined in `blocks/connectors.py` (value `1e-4` mm), so a bore exactly as deep as the wall thickness cuts clean. Lateral dimensions (diameter, peak height) SHALL NOT be affected by `_EPS`.

#### Scenario: Bore as deep as the wall cuts clean
- **WHEN** `teardrop_bore` is subtracted from a wall whose thickness equals the `depth` argument
- **THEN** the resulting solid is watertight with no coincident faces on the far surface

#### Scenario: Lateral dimensions unaffected by epsilon
- **WHEN** `teardrop_bore(d=8.0, depth=4.0)` is called
- **THEN** the circular portion has diameter 8.0 mm and the extrusion length along the bore axis equals `4.0 + _EPS`

### Requirement: Block is registered in the inventory and exported

The system SHALL register `teardrop_bore` in `blocks/inventory.json` with a descriptor including `name`, `module` (`blocks.connectors`), `function`, `use`, `params`, `dimensions`, and `interfaces`, and SHALL re-export it from the `blocks` package `__init__`. The descriptor SHALL declare one interface of type `axis` oriented along the bore.

#### Scenario: Inventory lookup
- **WHEN** the orchestrator looks up `"teardrop_bore"` in `blocks/inventory.json`
- **THEN** it receives the full descriptor including params and an `axis` interface

#### Scenario: Import from the blocks package
- **WHEN** a model script runs `from blocks import teardrop_bore`
- **THEN** the import succeeds and the function is callable
