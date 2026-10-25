"""Archetype: snap-fit lid. Flat panel with two cantilever snap_hook_clip features
mounted on the underside near the north/south edges, embedded slightly into the panel
so the union is a real volumetric overlap rather than a coincident-face touch. Mate
each clip with a snap_socket_receiver cut into the enclosure body's matching wall.

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("lid_snap")
panel = part.select("box", id="panel")
part.resize(panel)
part.place(panel, op="base")

# Clips are flipped hook-down; each planned point is the beam's top face, embedded in
# the panel underside. The south clip faces -Y.
clip = part.select("snap_hook_clip", id="clip")
part.resize(clip)
north, south = part.positions("clip")
part.place(clip, at=north, rotate=(0, 180, 0), op="union")
part.place(clip, at=south, rotate=(0, 180, 180), op="union")

result = part.result()
