"""Archetype: flat plate with a boss pattern. A flat rectangular plate with a regular
grid of screw bosses unioned onto the top face, for mounting a PCB or panel of
components. Combine with vent_grid or port_cutout for enclosure-adjacent plates.

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("plate_boss_pattern")
plate = part.select("box", id="plate")
part.resize(plate)
part.place(plate, op="base")

standoff = part.select("pcb_standoff", id="standoff")
part.resize(standoff)
top = part.param("plate", "h")
part.place(standoff, at=[(x, y, top) for x, y, _ in part.positions("standoff")], op="union")

result = part.result()
