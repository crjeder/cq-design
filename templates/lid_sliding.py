"""Archetype: sliding dovetail lid. The tongue IS the lid -- height equals thickness, so
it sits flush with the box top. Slides along +Y into a dovetail_groove cut into the
mating enclosure body's inner top edge (width/wall/angle must match the groove).

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("lid_sliding")
lid = part.select("dovetail_tongue", id="lid")
part.resize(lid)
part.place(lid, op="base")

result = part.result()
