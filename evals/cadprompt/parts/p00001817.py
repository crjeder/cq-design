import cadquery as cq

TOP_L, TOP_W, TOP_H = 1.20302, 0.55872, 0.020134
LEG, LEG_H = 0.060403, 0.75

top = cq.Workplane("XY").workplane(offset=LEG_H).rect(TOP_L, TOP_W).extrude(TOP_H)
dx, dy = (TOP_L - LEG) / 2, (TOP_W - LEG) / 2
legs = (
    cq.Workplane("XY")
    .pushPoints([(sx * dx, sy * dy) for sx in (-1, 1) for sy in (-1, 1)])
    .rect(LEG, LEG)
    .extrude(LEG_H)
)
result = top.union(legs)
