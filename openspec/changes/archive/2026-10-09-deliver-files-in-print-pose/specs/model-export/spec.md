## MODIFIED Requirements

### Requirement: Assembled-pose meshes for the kinematic check are preserved

The exporter SHALL produce one assembled-pose per-union mesh per union, in the union's `placement` pose, as the source of truth consumed by the whole-model checks. These meshes SHALL NOT be used as user deliverables, and producing print-pose deliverables SHALL NOT alter them.

#### Scenario: Print-pose deliverables do not disturb the check meshes
- **WHEN** `build.py` delivers print-pose files
- **THEN** the per-union assembled-pose meshes consumed by the checks are still written in each union's `placement` pose

#### Scenario: Deliverable STL is not copied from the assembly output
- **WHEN** `build.py --formats stl` runs while the assembly directory is current
- **THEN** `<union>.stl` is exported in print pose rather than copied from the assembly directory
