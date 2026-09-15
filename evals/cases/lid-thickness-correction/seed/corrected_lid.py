"""Lid plate with an inner locating lip."""

import cadquery as cq

PLATE_W = 70.0
PLATE_D = 50.0
PLATE_T = 3.0
LIP_W = 66.0
LIP_D = 46.0
LIP_T = 1.0  # round 1: lip wall

plate = cq.Workplane("XY").box(PLATE_W, PLATE_D, PLATE_T, centered=(True, True, False))
lip = (
    cq.Workplane("XY")
    .box(LIP_W, LIP_D, LIP_T, centered=(True, True, False))
    .translate((0, 0, -LIP_T))
)
result = plate.union(lip)
