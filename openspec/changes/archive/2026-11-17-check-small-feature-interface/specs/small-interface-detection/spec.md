## ADDED Requirements

### Requirement: Interface area of a union step
For every `union` step of a step-form part, the skill SHALL compute the interface area between the placed tool and the body so far from B-rep geometry, without meshing. The area SHALL be the smaller of (a) the area of the body's faces that lie inside the tool (or coincide with a tool face) and (b) the area of the tool's faces that lie inside the body (or coincide with a body face), so a tool that only touches the body is measured by its contact faces. A tool that touches only along an edge or at a point SHALL have area 0. When one step places a tool at several points, each placed copy SHALL be measured on its own against the body so far.

#### Scenario: Cone resting on a cube face
- **WHEN** a cone's flat base lies on the top face of a cube
- **THEN** the interface area equals the area of the cone's base

#### Scenario: Cone sunk slightly into a cube face
- **WHEN** a cone's base lies 0.1 mm below the top face of a cube
- **THEN** the interface area equals the area of the cone's cross-section at the cube's top face, not the area of the cone's sunk surface

#### Scenario: Cone placed on a cube edge
- **WHEN** a cone's base is centred on the edge of a cube's top face
- **THEN** the interface area is half the cone's base area

#### Scenario: Cone beyond a cube edge
- **WHEN** a cone's base lies fully past the edge so that it only touches the cube along that edge
- **THEN** the interface area is 0

#### Scenario: Post on three slivers
- **WHEN** a post's underside touches a grid through three 0.2 x 1 mm patches
- **THEN** the interface area is the sum of the three patches, about 0.6 mm^2

#### Scenario: Several placement points
- **WHEN** one place step puts the same post at four points, three of them on a 3 mm column and one on a sliver
- **THEN** the sliver copy is reported on its own, with its own location

### Requirement: Small interfaces fail the step
When a union step's interface area is below `interface_min_area_mm2`, the step SHALL fail with a `small_interface` error carrying `area_mm2`, `equiv_diameter_mm`, the threshold, the placed instance id, the instance it joins (when known), the interface centroid `location_xyz_mm`, and a remedy `hint`. The hint SHALL offer a footprint at or above the threshold, such as a column from the feature down to the build plate, and SHALL NOT claim a guaranteed fix. A fused-in tool whose interface is at or above the threshold SHALL pass.

#### Scenario: Error carries its fields
- **WHEN** a union step's interface is 0.6 mm^2 and the threshold is 4.0
- **THEN** the step fails with a `small_interface` error holding `area_mm2`, `equiv_diameter_mm`, the threshold, the instance id, `location_xyz_mm`, and a `hint`

#### Scenario: Post on a 3 mm column
- **WHEN** a post is placed on a 3 mm diameter column (about 7 mm^2)
- **THEN** the step passes

#### Scenario: Interface of a cut or base step
- **WHEN** a step is a `cut` or the first `base` placement
- **THEN** no interface is measured and no `small_interface` error is raised

### Requirement: Interface area is recorded in the step report
Every `union` step in the step report SHALL carry an `interface` entry with `area_mm2` (and `location_xyz_mm`), so the builder and auditor can read it even when the step passes.

#### Scenario: Passing union step
- **WHEN** a union step passes with an interface of 7.1 mm^2
- **THEN** its step record shows `interface.area_mm2` of about 7.1

#### Scenario: Cached step
- **WHEN** a union step is served from the step cache
- **THEN** its `interface` entry is the same as when it first ran
