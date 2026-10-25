"""Archetype: phone/tablet stand. A wedge-shaped base with a flat vertical back section
and a sloped front ramp, with a slot cut into the flat back section that holds a flat
device at a fixed viewing angle. Use for phone stands, tablet stands, and card/photo
holders.

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("stand")
# YZ wedge profile extruded along X, centered on X.
wedge = part.select("prism", id="wedge")
part.resize(wedge)
part.place(wedge, at=(-part.param("wedge", "h") / 2, 0, 0), rotate=(90, 0, 90), op="base")

# The slot box overshoots the top by 1 mm; its planned position is the cut's center.
slot = part.select("box", id="slot")
part.resize(slot)
x, y, z = part.positions("slot")[0]
part.place(slot, at=(x, y, z - part.param("slot", "h") / 2 + 0.5), op="cut")

result = part.result()
