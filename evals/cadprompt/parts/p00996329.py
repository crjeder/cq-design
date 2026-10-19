import cadquery as cq

T = 0.083333
LEG = 0.75
DEPTH = 0.333333

result = (
    cq.Workplane("XY")
    .polyline([(0, 0), (LEG, 0), (LEG, T), (T, T), (T, LEG), (0, LEG)])
    .close()
    .extrude(DEPTH)
)
