"""Archetype: screwed lid. Flat panel with a 2x2 corner counterbore pattern so a screw
head sits flush with the top face and the shaft passes through into the mating
enclosure body's screw_boss (or heat_set_boss) pattern below.

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("lid_screwed")
panel = part.select("box", id="panel")
part.resize(panel)
part.place(panel, op="base")

cbore = part.select("counterbore_hole", id="cbore")
part.resize(cbore)
part.place(cbore, at=[(x, y, 0) for x, y, _ in part.positions("cbore")], op="cut")

result = part.result()
