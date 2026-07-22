"""Archetype: flanged adapter ring. A stepped cylindrical bore adapter with a flat
mounting flange at one end, drilled with a bolt-circle pattern. Use to adapt between
two circular fittings of different diameter (pipe couplers, lens/filter adapters,
motor-to-shaft collars, vacuum-port reducers)."""

import math

import cadquery as cq

from cq_verify import verify_boolean

# PARAMETERS
bore_d = 20.0  # mm through-bore diameter (the smaller mating fitting)
body_d = 32.0  # mm cylindrical body outer diameter (the larger mating fitting)
body_h = 15.0  # mm cylindrical body height
flange_d = 45.0  # mm flange outer diameter
flange_t = 3.0  # mm flange thickness
bolt_circle_d = 38.0  # mm bolt-circle diameter for the flange mounting holes
bolt_hole_d = 3.4  # mm mounting hole clearance diameter (M3)
bolt_count = 4  # count of mounting holes evenly spaced on the bolt circle

body = cq.Workplane("XY").circle(body_d / 2).extrude(body_h)
flange = cq.Workplane("XY").circle(flange_d / 2).extrude(flange_t)
ring = verify_boolean(flange, flange.union(body), "union", "body_on_flange")

bore = cq.Workplane("XY").circle(bore_d / 2).extrude(body_h + flange_t)
ring = verify_boolean(ring, ring.cut(bore), "cut", "through_bore")

bolt_r = bolt_circle_d / 2
bolt_positions = [
    (
        bolt_r * math.cos(2 * math.pi * i / bolt_count),
        bolt_r * math.sin(2 * math.pi * i / bolt_count),
    )
    for i in range(bolt_count)
]
bolt_holes = cq.Workplane("XY").pushPoints(bolt_positions).circle(bolt_hole_d / 2).extrude(flange_t)
ring = verify_boolean(ring, ring.cut(bolt_holes), "cut", "bolt_circle")

result = ring
