import cadquery as cq

L, W, H = 1.23418, 0.617188, 0.75
STUD_D, STUD_H, PAD = 0.380469, 0.140625, 0.118359

body = cq.Workplane("XY").box(L, W, H, centered=(True, True, False))
x = L / 2 - PAD - STUD_D / 2
studs = cq.Workplane("XY").pushPoints([(-x, 0), (x, 0)]).circle(STUD_D / 2).extrude(-STUD_H)
result = body.union(studs)
