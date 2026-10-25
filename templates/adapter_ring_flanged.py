"""Archetype: flanged adapter ring. A stepped cylindrical bore adapter with a flat
mounting flange at one end, drilled with a bolt-circle pattern. Use to adapt between
two circular fittings of different diameter (pipe couplers, lens/filter adapters,
motor-to-shaft collars, vacuum-port reducers).

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("adapter_ring_flanged")
flange = part.select("cylinder", id="flange")
part.resize(flange)
part.place(flange, op="base")

body = part.select("cylinder", id="body")
part.resize(body)
part.place(body, op="union")

bore = part.select("cylinder", id="bore")
part.resize(bore)
part.place(bore, op="cut")

bolt = part.select("cylinder", id="bolt")
part.resize(bolt)
part.place(bolt, at=[(x, y, 0) for x, y, _ in part.positions("bolt")], op="cut")

result = part.result()
