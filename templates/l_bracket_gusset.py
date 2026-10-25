"""Archetype: L-bracket with a triangular gusset. Two rectangular arms meeting at a
right angle, each drilled with a mounting-screw clearance hole, reinforced by a
diagonal gusset rib across the inner corner. Use for wall/shelf mounts and right-angle
structural brackets.

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("l_bracket_gusset")
arm_v = part.select("box", id="arm_v")
part.resize(arm_v)
part.place(arm_v, op="base")

# The horizontal arm starts at X=0 and runs along +X.
arm_h = part.select("box", id="arm_h")
part.resize(arm_h)
part.place(arm_h, at=(part.param("arm_h", "w") / 2, 0, 0), op="union")

# XY profile stood up into the XZ plane, centered on Y.
gusset = part.select("prism", id="gusset")
part.resize(gusset)
part.place(gusset, at=(0, part.param("gusset", "h") / 2, 0), rotate=(90, 0, 0), op="union")

# Hole cylinders are centered on their planned positions along their axis.
hole_v = part.select("cylinder", id="hole_v")
part.resize(hole_v)
x, y, z = part.positions("hole_v")[0]
part.place(hole_v, at=(x - part.param("hole_v", "h") / 2, y, z), rotate=(0, 90, 0), op="cut")

hole_h = part.select("cylinder", id="hole_h")
part.resize(hole_h)
x, y, z = part.positions("hole_h")[0]
part.place(hole_h, at=(x, y, z - part.param("hole_h", "h") / 2), op="cut")

result = part.result()
