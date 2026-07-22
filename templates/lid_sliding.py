"""Archetype: sliding dovetail lid. The tongue IS the lid -- height equals thickness, so
it sits flush with the box top. Slides along +Y into a dovetail_groove cut into the
mating enclosure body's inner top edge (width/wall/angle must match the groove)."""

from blocks import dovetail_tongue

# PARAMETERS
box_width = 60.0  # mm outer box width (must match the mating body's width)
wall = 2.0  # mm box wall thickness (must match the mating body's wall)
lid_t = 3.0  # mm lid thickness (equals dovetail depth)
lid_length = 36.0  # mm lid length along the slide direction (+Y), typically box_depth - wall
dovetail_angle = 55.0  # degrees from vertical (default 55; keep >= 45 for printability)
clearance = 0.1  # mm per-side clearance for smooth sliding (0.05 for a snug fit)

result = dovetail_tongue(box_width, wall, lid_t, lid_length, dovetail_angle, clearance)
