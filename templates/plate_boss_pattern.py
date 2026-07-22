"""Archetype: flat plate with a boss pattern. A flat rectangular plate with a regular
grid of screw bosses unioned onto the top face, for mounting a PCB or panel of
components. Combine with vent_grid or port_cutout for enclosure-adjacent plates."""

from typing import cast

import cadquery as cq

from blocks import fillet_box, pcb_standoff
from cq_verify import verify_boolean

# PARAMETERS
plate_w = 60.0  # mm plate width (X)
plate_d = 50.0  # mm plate depth (Y)
plate_t = 3.0  # mm plate thickness
corner_r = 3.0  # mm outer corner fillet radius (0 = sharp)
boss_cols = 2  # count of boss columns (X)
boss_rows = 2  # count of boss rows (Y)
boss_spacing_x = 40.0  # mm spacing between boss columns
boss_spacing_y = 30.0  # mm spacing between boss rows
boss_d_screw = 2.5  # mm screw clearance diameter
boss_d_outer = 6.0  # mm boss outer diameter
boss_h = 6.0  # mm standoff height above the plate top face

plate = fillet_box(plate_w, plate_d, plate_t, corner_r)

boss_positions = [
    (
        -boss_spacing_x * (boss_cols - 1) / 2 + c * boss_spacing_x,
        -boss_spacing_y * (boss_rows - 1) / 2 + r * boss_spacing_y,
    )
    for r in range(boss_rows)
    for c in range(boss_cols)
]
bosses = (
    cq.Workplane("XY")
    .workplane(offset=plate_t)
    .pushPoints(boss_positions)
    .eachpoint(
        lambda loc: cast(cq.Shape, pcb_standoff(boss_d_screw, boss_d_outer, boss_h).val()).moved(
            loc
        ),
        combine=True,
    )
)
plate = verify_boolean(plate, plate.union(bosses), "union", "boss_grid")

result = plate
