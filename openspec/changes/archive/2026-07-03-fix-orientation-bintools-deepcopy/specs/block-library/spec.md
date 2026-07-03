## ADDED Requirements

### Requirement: cq_warehouse is imported only when a hardware block needs it

The block library SHALL NOT import `cq_warehouse` (and SHALL NOT leave installed the
global `Shape` monkeypatch that `cq_warehouse.extensions` applies) merely as a side
effect of importing the block package or the hardware module. Importing `blocks` or
`blocks.hardware` SHALL succeed without `cq_warehouse` present in `sys.modules` and
without replacing cadquery's native `Shape._apply_transform`/`Shape.copy`. Each hardware
block that requires `cq_warehouse` SHALL import it inside the function body:
`cq_warehouse.extensions` SHALL be loaded only inside the function that uses
`Workplane.insertHole` (`heat_set_boss`), and the fastener classes only inside the
functions that build them.

#### Scenario: Importing the block package does not load cq_warehouse

- **WHEN** a model script runs `from blocks import fillet_box` (or imports
  `blocks.hardware`) and calls no hardware function
- **THEN** `cq_warehouse` is not imported, `sys.modules` contains no `cq_warehouse`
  entry, and `Shape._apply_transform` retains cadquery's native implementation

#### Scenario: Hardware function still works via lazy import

- **WHEN** `heat_set_boss(...)` is called
- **THEN** `cq_warehouse.extensions` is loaded on demand, `Workplane.insertHole` is
  available, and the function returns a valid `cq.Workplane` solid

#### Scenario: Non-insert hardware blocks do not require the extension

- **WHEN** `socket_head_cap_screw`, `hex_head_screw`, or `hex_nut` is called
- **THEN** the function builds its fastener solid via a function-local fastener-class
  import and returns a valid `cq.Workplane`
