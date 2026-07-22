"""Archetype: enclosure body. Open-top hollow box with an optional 2x2 corner
screw-boss pattern for a self-tapping-screw lid. Mate with lid_screwed (or any
lid template) placed on top."""

from typing import cast

import cadquery as cq

from blocks import hollow_box, screw_boss
from cq_verify import verify_boolean

# PARAMETERS
width = 60.0  # mm outer width (X)
depth = 40.0  # mm outer depth (Y)
height = 25.0  # mm outer height (Z)
wall = 2.0  # mm wall thickness
floor_t = 2.0  # mm floor thickness
corner_r = 3.0  # mm outer corner fillet radius (0 = sharp)
add_bosses = True  # union a 2x2 corner screw-boss pattern onto the floor
boss_margin = 8.0  # mm inset of each boss center from the outer corner
boss_d_screw = 2.5  # mm self-tapping screw diameter
boss_d_outer = 6.0  # mm boss outer diameter
boss_h = 8.0  # mm boss height measured from Z=0

body = hollow_box(width, depth, height, wall, floor_t, corner_r)

if add_bosses:
    boss_x = width / 2 - boss_margin
    boss_y = depth / 2 - boss_margin
    boss_positions = [
        (boss_x, boss_y),
        (-boss_x, boss_y),
        (-boss_x, -boss_y),
        (boss_x, -boss_y),
    ]
    bosses = (
        cq.Workplane("XY")
        .pushPoints(boss_positions)
        .eachpoint(
            lambda loc: cast(cq.Shape, screw_boss(boss_d_screw, boss_d_outer, boss_h).val()).moved(
                loc
            ),
            combine=True,
        )
    )
    body = verify_boolean(body, body.union(bosses), "union", "corner_bosses")

result = body
