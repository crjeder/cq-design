## ADDED Requirements

### Requirement: Groove geometry is a trapezoid wider at base than opening
`dovetail_groove` SHALL return a `cq.Workplane` whose cross-section in the XZ plane is a trapezoid with opening width `width - 2*wall` at Z=depth and base width `width - 2*wall + 2*flare` at Z=0, where `flare = tan(radians(90 - angle)) * depth`. The solid SHALL extend from Y=0 to Y=length.

#### Scenario: Default angle produces correct flare
- **WHEN** `dovetail_groove(width=26, wall=3, depth=2, length=30)` is called
- **THEN** the bounding box width at base SHALL be `(26 - 6) + 2 * tan(radians(35)) * 2` ≈ 22.8 mm

#### Scenario: Groove opening equals width minus two walls
- **WHEN** `dovetail_groove(width=30, wall=3, depth=2, length=30)` is called
- **THEN** the bounding box X-span at Z=depth SHALL equal `30 - 2*3 = 24` mm

#### Scenario: Groove is centered in X
- **WHEN** `dovetail_groove` is called with any `width` and `wall`
- **THEN** the groove bounding box SHALL be symmetric about X=0

#### Scenario: Groove base is at Z=0
- **WHEN** `dovetail_groove` is called
- **THEN** `bb.zmin` SHALL be 0 and `bb.zmax` SHALL equal `depth`

### Requirement: Tongue geometry matches groove minus clearance
`dovetail_tongue` SHALL return a `cq.Workplane` whose cross-section matches the groove profile with both top and base widths reduced by `2*clearance`. The solid SHALL extend from Y=0 to Y=length and have height equal to `depth`.

#### Scenario: Tongue opening equals groove opening minus clearance
- **WHEN** `dovetail_tongue(width=26, wall=3, depth=2, length=30, clearance=0.1)` is called
- **THEN** the bounding box X-span at Z=depth SHALL equal `(26 - 6) - 2*0.1 = 19.8` mm

#### Scenario: Tongue fits inside groove
- **WHEN** `dovetail_tongue` and `dovetail_groove` are called with the same `width`, `wall`, `depth`, `length`, `angle`
- **THEN** the tongue bounding box X-span SHALL be less than the groove's bounding box X-span by exactly `2*clearance` at every Z slice

#### Scenario: Tongue height equals depth
- **WHEN** `dovetail_tongue` is called with `depth=2`
- **THEN** `bb.zmax - bb.zmin` SHALL equal 2.0

#### Scenario: Tongue is centered in X
- **WHEN** `dovetail_tongue` is called with any `width`, `wall`, and `clearance`
- **THEN** the bounding box SHALL be symmetric about X=0

### Requirement: Both blocks use the same angle parameter semantics
`angle` SHALL be measured in degrees from vertical. At `angle=55`, the overhang from horizontal is 35 degrees, which is below the 45-degree FDM printability threshold.

#### Scenario: Angle at 45 degrees produces flare equal to depth
- **WHEN** `dovetail_groove(width=26, wall=3, depth=2, length=30, angle=45)` is called
- **THEN** the groove SHALL be valid (no exception) and `flare` SHALL equal `depth` (since tan(45°) = 1)

#### Scenario: Shallow angle below 45 degrees returns valid geometry
- **WHEN** `angle < 45` is passed (overhang > 45 degrees from horizontal)
- **THEN** the function SHALL still return valid geometry (printability is the caller's concern)

### Requirement: Inventory entries are present and schema-valid
`blocks/inventory.json` SHALL contain entries for `dovetail_groove` and `dovetail_tongue` that pass validation against `blocks/inventory_schema.json`.

#### Scenario: dovetail_groove entry includes wall parameter
- **WHEN** `blocks/inventory.json` is validated against the schema
- **THEN** the `dovetail_groove` entry SHALL pass with `module: blocks.joints`, `params` including `wall`, and at least one `sliding_interface` interface

#### Scenario: dovetail_tongue entry includes wall and clearance parameters
- **WHEN** `blocks/inventory.json` is validated against the schema
- **THEN** the `dovetail_tongue` entry SHALL pass with `module: blocks.joints`, `params` including `wall` and `clearance`, and at least one `sliding_interface` interface
