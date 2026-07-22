"""Archetype: U-clip. A U-shaped spring clip: a solid closed base at one end (Y=0) with
two parallel arms extending in +Y, separated by a gap sized to grip a panel or rail edge
by friction/spring-back. Use for cable clips, panel edge trim, badge clips, and
rail-mount clips."""

import cadquery as cq

from cq_verify import verify_boolean

# PARAMETERS
clip_width = 15.0  # mm clip width (X, constant along the whole clip)
gap_mm = 4.0  # mm inner gap the clip grips (panel/rail thickness + a small squeeze)
wall_t = 2.0  # mm wall thickness (also the closed base thickness at the bend)
arm_len = 12.0  # mm straight arm length beyond the closed base, on each side

outer_h = gap_mm + 2 * wall_t
total_len = arm_len + wall_t

outer = cq.Workplane("XY").box(clip_width, total_len, outer_h, centered=(True, False, False))
inner = (
    cq.Workplane("XY")
    .box(clip_width + 1, total_len, gap_mm, centered=(True, False, False))
    .translate((0, wall_t, wall_t))
)
result = verify_boolean(outer, outer.cut(inner), "cut", "u_channel")
