# shape-transform-safety

## Purpose

Guarantee that importing `cq_warehouse` does not leave cadquery's global `Shape` copy and
transform methods replaced with a serialization-based implementation that crashes on some
OCCT 7.8 geometry.

## Requirements

### Requirement: Importing cq_warehouse does not leave Shape.copy serialization-based

Loading `cq_warehouse.extensions` for its `Workplane` side effects SHALL NOT leave the
global `cadquery.occ_impl.shapes.Shape.copy` (or `Shape._apply_transform`) replaced with
the `copy.deepcopy`-based implementation that performs a `BinTools` serialize/deserialize
round-trip. After the skill's hardware blocks are imported, `Shape.copy` SHALL be
cadquery's native `BRepBuilderAPI_Copy`-based implementation.

The mechanism SHALL be idempotent (safe to invoke from multiple import sites) and SHALL
preserve all other `cq_warehouse.extensions` side effects, including `Workplane.insertHole`
and the fastener classes.

#### Scenario: Hardware blocks import restores native copy

- **WHEN** `blocks.hardware` (or any module that loads `cq_warehouse.extensions` through
  the skill's shim) is imported
- **THEN** `cq_warehouse.extensions` is loaded and `Workplane.insertHole` is available
- **AND** `cadquery.occ_impl.shapes.Shape.copy` is the native implementation, not the
  `deepcopy`-based patch

#### Scenario: Transform of round-trip-hostile geometry does not crash

- **WHEN** `cq_warehouse.extensions` has been loaded through the shim and a shape whose
  `BinTools` write/read round-trip would raise `BinTools_SurfaceSet::ReadGeometry` is
  copied, rotated, and translated
- **THEN** the operations complete without raising a `Standard_Failure`
- **AND** the result exports to a valid (watertight) STL

#### Scenario: Fastener integration still works

- **WHEN** a model script instantiates `cq_warehouse` fastener classes and uses
  `Workplane.insertHole` after the shim has run
- **THEN** the fastener geometry and bored holes are produced exactly as before the change
