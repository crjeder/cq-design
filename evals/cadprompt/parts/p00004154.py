import cadquery as cq

L, W, H, R = 0.70588, 0.40809, 0.22059, 0.08

result = cq.Workplane("XY").box(L, W, H, centered=(True, True, False)).edges("|Z").fillet(R)
