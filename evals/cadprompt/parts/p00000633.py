import cadquery as cq

result = cq.Workplane("XY").box(0.75, 0.1875, 0.00391).faces(">Z").workplane().hole(0.12512)
