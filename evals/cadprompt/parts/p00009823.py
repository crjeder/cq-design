import cadquery as cq

SIDE = 1.5
HEIGHT = 0.016238

# regular hexagon: circumradius == side length
result = cq.Workplane("XY").polygon(6, 2 * SIDE).extrude(HEIGHT)
