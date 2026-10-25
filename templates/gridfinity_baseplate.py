"""Archetype: Gridfinity baseplate. A cols x rows grid of sockets that Gridfinity bins drop
into, 42 mm per cell so plates tile edge to edge with no gap. The default 4.75 mm thickness
is the minimal open-bottom plate; raise plate_h to leave stock under the sockets for magnets
or mounting screws.

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("gridfinity_baseplate")
plate = part.select("gridfinity_baseplate", id="plate")
part.resize(plate)
part.place(plate, op="base")

result = part.result()
