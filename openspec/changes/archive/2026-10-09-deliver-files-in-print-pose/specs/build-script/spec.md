## ADDED Requirements

### Requirement: Every requested deliverable format is in print pose

`build/build.py` SHALL write every requested format (`3mf`, `stl`, `step`, `obj`, `iges`, `scad`) with each union in its print pose: the union's build-pose (authored) geometry rotated by its accepted or recomputed orientation. A union with no orientation SHALL be written in build pose. No requested format SHALL be written in assembly pose. Multi-union plate STLs SHALL remain fused in their assembled relative poses and rotated into print pose.

#### Scenario: Per-union STL is in print pose
- **WHEN** `build.py --formats stl` runs and a union has an accepted `rotate`
- **THEN** `<union>.stl` is the build-pose geometry rotated by that `rotate`, not the assembly-pose mesh

#### Scenario: STEP, OBJ, IGES and SCAD are in print pose
- **WHEN** `build.py --formats step,obj,iges,scad` runs
- **THEN** each `<union>.<ext>` is in the union's print pose

#### Scenario: Union without orientation falls back to build pose
- **WHEN** a union has no orientation entry
- **THEN** its files are written in build pose, never assembly pose

### Requirement: User-facing directions are in build pose

All directions given by the user or recorded in the plan or CLI flags (`load.dir`, `show_face`, `--load`, `--show-face`, face and axis names in conversation) SHALL be interpreted in the part's build pose. The accepted orientation's `rotate` SHALL be the only mapping from build pose to print pose.

#### Scenario: Load direction is build pose
- **WHEN** a part declares `load.dir` and its print orientation is chosen
- **THEN** the direction is applied to the part-frame mesh before the print rotation, and the rotation is reported as build -> print
