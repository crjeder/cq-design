"""Archetype: screwed lid. Flat panel with a 2x2 corner counterbore pattern so a screw
head sits flush with the top face and the shaft passes through into the mating
enclosure body's screw_boss (or heat_set_boss) pattern below."""

from typing import cast

import cadquery as cq

from blocks import counterbore_hole, fillet_box
from cq_verify import verify_boolean

# PARAMETERS
lid_width = 60.0  # mm outer lid width (X), matches the enclosure body's outer width
lid_depth = 40.0  # mm outer lid depth (Y), matches the enclosure body's outer depth
lid_t = 3.0  # mm lid panel thickness
corner_r = 3.0  # mm outer corner fillet radius (0 = sharp)
hole_margin = 8.0  # mm inset of each hole center from the outer corner (match boss_margin)
d_screw = 2.5  # mm screw shaft clearance diameter
d_head = 5.0  # mm counterbore pocket diameter
h_head = 1.5  # mm counterbore pocket depth (< lid_t)

panel = fillet_box(lid_width, lid_depth, lid_t, corner_r)

hole_x = lid_width / 2 - hole_margin
hole_y = lid_depth / 2 - hole_margin
hole_positions = [
    (hole_x, hole_y),
    (-hole_x, hole_y),
    (-hole_x, -hole_y),
    (hole_x, -hole_y),
]
holes = (
    cq.Workplane("XY")
    .pushPoints(hole_positions)
    .eachpoint(
        lambda loc: cast(cq.Shape, counterbore_hole(d_screw, d_head, h_head, lid_t).val()).moved(
            loc
        ),
        combine=True,
    )
)

panel = verify_boolean(panel, panel.cut(holes), "cut", "corner_counterbores")

result = panel
