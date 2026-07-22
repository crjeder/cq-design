"""Archetype: phone/tablet stand. A wedge-shaped base with a flat vertical back section
and a sloped front ramp, with a slot cut into the flat back section that holds a flat
device at a fixed viewing angle. Use for phone stands, tablet stands, and card/photo
holders."""

import cadquery as cq

from cq_verify import verify_boolean

# PARAMETERS
base_w = 80.0  # mm base width (X)
base_d = 70.0  # mm base footprint depth (Y), back edge to front edge
base_h = 45.0  # mm base height at the back (Z)
back_flat_w = 20.0  # mm depth of the flat vertical back section that holds the slot
slot_w = 74.0  # mm slot width (X), slightly less than base_w
slot_gap = 6.0  # mm slot opening width (device thickness + clearance)
slot_depth = 15.0  # mm how far the slot cuts down into the back section from the top

wedge_pts = [(0, 0), (base_d, 0), (back_flat_w, base_h), (0, base_h)]
wedge = cq.Workplane("YZ").polyline(wedge_pts).close().extrude(base_w / 2, both=True)

slot_y_center = back_flat_w / 2
slot = (
    cq.Workplane("XY")
    .workplane(offset=base_h - slot_depth)
    .transformed(offset=(0, slot_y_center, 0))
    .box(slot_w, slot_gap, slot_depth + 1, centered=(True, True, False))
)
result = verify_boolean(wedge, wedge.cut(slot), "cut", "device_slot")
