"""Archetype: Gridfinity storage bin. A spec-conformant bin on the 42 mm Gridfinity grid --
feet, walls, cavity, and stacking lip -- with optional dividers, a label shelf, a finger
scoop, and magnet/screw pockets. Footprint is 42*cols-0.5 by 42*rows-0.5 mm and the body
is 7*height_u mm tall, so it drops into any baseplate and stacks with any other bin.

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("gridfinity_bin")
bin_ = part.select("gridfinity_bin", id="bin")
part.resize(bin_)
part.place(bin_, op="base")

result = part.result()
