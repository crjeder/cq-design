"""Archetype: wall hook. A flat wall-mount backplate with two screw clearance holes and
a curved round-rod arm (built as a partial revolve) unioned onto the front face,
curling out and back to retain a hung item. Use for coat hooks, cable hooks, and tool
hangers."""

import cadquery as cq

from cq_verify import verify_boolean

# PARAMETERS
plate_w = 25.0  # mm backplate width (X)
plate_h = 40.0  # mm backplate height (Z)
plate_t = 5.0  # mm backplate thickness (Y)
hook_arm_r = 14.0  # mm centerline radius of the hook arm's curve
hook_tube_d = 8.0  # mm hook arm cross-section (round rod) diameter
hook_sweep_deg = 200.0  # degrees the arm curls away from its pivot
hook_pivot_z = 20.0  # mm pivot height on the backplate (Z)
mount_hole_d = 4.3  # mm mounting screw clearance diameter (M4)
mount_hole_inset = 8.0  # mm inset of each mounting hole from the backplate's top/bottom edge

plate = cq.Workplane("XY").box(plate_w, plate_t, plate_h, centered=(True, False, False))

pivot_y = plate_t / 2
arm = (
    cq.Workplane("XZ")
    .transformed(offset=(0, hook_pivot_z, pivot_y))
    .moveTo(0, hook_arm_r)
    .circle(hook_tube_d / 2)
    .revolve(hook_sweep_deg, (0, 0), (1, 0))
)
plate = verify_boolean(plate, plate.union(arm), "union", "hook_arm")

mount_hole_z_top = plate_h - mount_hole_inset
mount_hole_z_bottom = mount_hole_inset
top_hole = cq.Workplane("XY").add(
    cq.Solid.makeCylinder(
        mount_hole_d / 2,
        plate_t + 1,
        pnt=cq.Vector(0, 0, mount_hole_z_top),
        dir=cq.Vector(0, 1, 0),
    )
)
bottom_hole = cq.Workplane("XY").add(
    cq.Solid.makeCylinder(
        mount_hole_d / 2,
        plate_t + 1,
        pnt=cq.Vector(0, 0, mount_hole_z_bottom),
        dir=cq.Vector(0, 1, 0),
    )
)
plate = verify_boolean(plate, plate.cut(top_hole), "cut", "top_mount_hole")
plate = verify_boolean(plate, plate.cut(bottom_hole), "cut", "bottom_mount_hole")

result = plate
