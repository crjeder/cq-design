"""Archetype: wall hook. A flat wall-mount backplate with two screw clearance holes and
a curved round-rod arm (built as a partial revolve) unioned onto the front face,
curling out and back to retain a hung item. Use for coat hooks, cable hooks, and tool
hangers.

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("hook")
plate = part.select("box", id="plate")
part.resize(plate)
part.place(plate, at=(0, part.param("plate", "d") / 2, 0), op="base")

# The arm curls 'angle' degrees around an X axis through its planned pivot, starting
# straight above it.
arm = part.select("torus", id="arm")
part.resize(arm)
part.place(arm, at=part.positions("arm")[0], rotate=(0, 270, 180), op="union")

# Holes run along +Y from the plate back face.
hole = part.select("cylinder", id="mount_hole")
part.resize(hole)
holes = [(x, 0, z) for x, _, z in part.positions("mount_hole")]
part.place(hole, at=holes, rotate=(-90, 0, 0), op="cut")

result = part.result()
