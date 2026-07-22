"""Archetype: L-bracket with a triangular gusset. Two rectangular arms meeting at a
right angle, each drilled with a mounting-screw clearance hole, reinforced by a
diagonal gusset rib across the inner corner. Use for wall/shelf mounts and right-angle
structural brackets."""

import cadquery as cq

from cq_verify import verify_boolean

# PARAMETERS
arm_a_len = 40.0  # mm length of the vertical arm (Z)
arm_b_len = 40.0  # mm length of the horizontal arm (X)
arm_w = 20.0  # mm arm width (Y)
arm_t = 4.0  # mm arm thickness
gusset_t = 4.0  # mm gusset thickness (Y, centered in the arm width)
gusset_reach = 20.0  # mm how far the gusset extends along each arm from the inner corner
hole_d = 4.3  # mm mounting screw clearance diameter (M4)
hole_inset = 10.0  # mm inset of each hole center from its arm's free end

vertical_arm = cq.Workplane("XY").box(arm_t, arm_w, arm_a_len, centered=(True, True, False))
horizontal_arm = cq.Workplane("XY").box(arm_b_len, arm_w, arm_t, centered=(False, True, False))
bracket = verify_boolean(
    vertical_arm, vertical_arm.union(horizontal_arm), "union", "horizontal_arm"
)

gusset_profile = [
    (arm_t / 2, arm_t),
    (arm_t / 2 + gusset_reach, arm_t),
    (arm_t / 2, arm_t + gusset_reach),
]
gusset = cq.Workplane("XZ").polyline(gusset_profile).close().extrude(gusset_t / 2, both=True)
bracket = verify_boolean(bracket, bracket.union(gusset), "union", "gusset")

vertical_hole_z = arm_a_len - hole_inset
horizontal_hole_x = arm_b_len - hole_inset
vertical_hole = (
    cq.Workplane("XY").workplane(offset=vertical_hole_z).circle(hole_d / 2).extrude(arm_t + 1)
)
horizontal_hole = (
    cq.Workplane("XY")
    .transformed(offset=(horizontal_hole_x, 0, 0))
    .circle(hole_d / 2)
    .extrude(arm_t + 1)
)
bracket = verify_boolean(bracket, bracket.cut(vertical_hole), "cut", "vertical_hole")
bracket = verify_boolean(bracket, bracket.cut(horizontal_hole), "cut", "horizontal_hole")

result = bracket
