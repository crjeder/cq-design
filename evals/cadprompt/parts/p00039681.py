import cadquery as cq

# outer diameter is not given in the prompt; chosen to leave a wall around the larger bore
OD = 0.85
SMALL_ID, SMALL_H = 0.332143, 0.242143
LARGE_ID, LARGE_H = 0.728571, 0.321568

lower = cq.Workplane("XY").circle(OD / 2).circle(SMALL_ID / 2).extrude(SMALL_H)
upper = (
    cq.Workplane("XY")
    .workplane(offset=SMALL_H)
    .circle(OD / 2)
    .circle(LARGE_ID / 2)
    .extrude(LARGE_H)
)
result = lower.union(upper)
