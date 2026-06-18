## Context

CadQuery uses the OpenCASCADE (OCC) BREP kernel for boolean operations. When a subtractive solid is exactly flush with the face it should exit through, OCC encounters a coincident face -- two faces lying on the same plane, with no separation. The kernel may resolve this as a degenerate edge, leave a ghost face, or silently break the resulting shell's watertightness. Adding a small epsilon overcut ensures the cutter always exits cleanly on the far side of the material.

The blocks package has eight functions that return subtractive solids callers are expected to `.cut()` from a body: `counterbore_hole`, `countersink_hole`, `hex_nut_trap`, `alignment_socket`, `snap_socket_receiver` (fasteners.py) and `port_cutout`, `cable_slot`, `vent_grid` (connectors.py).

## Goals / Non-Goals

**Goals:**
- Guarantee all subtractive block functions overcut the material by `_EPS` on the extrusion axis.
- Define `_EPS` as a named constant so its meaning is clear and it is easy to tune.
- Keep the change invisible to callers -- no signature changes, no new parameters.

**Non-Goals:**
- Changing lateral dimensions (width, height of holes -- only depth/extrusion axis).
- Exposing epsilon as a user-configurable parameter.
- Applying epsilon to additive blocks (`screw_boss`, `pcb_standoff`, `alignment_pin`, etc.) -- those are never subtracted.

## Decisions

### Decision: epsilon value of `1e-4` mm

OCC's internal modeling tolerance is `1e-7` mm. FDM printers have a practical resolution floor of ~`0.1` mm. An epsilon of `1e-4` mm (0.1 micron) is:
- Three orders of magnitude above OCC's tolerance: guaranteed to produce a distinct face.
- Three orders of magnitude below FDM resolution: undetectable in the physical part.
- Representable exactly as a 64-bit float with no rounding error accumulation.

Alternative considered: `sys.float_info.epsilon` (~`2.2e-16`) -- too small; OCC may still treat coincident faces as degenerate at that scale. Alternative: `1e-3` mm -- works, but unnecessarily large for a precision kernel.

### Decision: one `_EPS` constant per module, not shared across modules

`fasteners.py` and `connectors.py` each define their own `_EPS = 1e-4`. This avoids a cross-module import for a single constant and makes each file self-contained. If the value ever needs to differ per module it is trivially adjustable.

### Decision: apply epsilon to the outermost extrusion only

In compound cutters (`counterbore_hole`, `countersink_hole`, `hex_nut_trap`) the shaft cylinder runs the full depth and is the component that exits the far face. Only the shaft's extrusion gets `+ _EPS`; the head pocket geometry is unaffected.

## Risks / Trade-offs

- [Volume change in tests] Volume-based assertions in `test_blocks.py` will see a tiny increase. Mitigation: the epsilon is `1e-4` mm on a depth of typically 2-20 mm, a relative error of `<0.005%` -- well within any reasonable floating-point tolerance used in tests.
- [Coincident-entry face] The epsilon adds length only on the exit side. The entry face remains flush with the top surface of the caller's body, which is correct -- the cutter must sit flush at the entry or the user's geometry will have an unwanted recess. No mitigation needed.
