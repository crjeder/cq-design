"""Archetype: Gridfinity storage bin. A spec-conformant bin on the 42 mm Gridfinity grid --
feet, walls, cavity, and stacking lip -- with optional dividers, a label shelf, a finger
scoop, and magnet/screw pockets. Footprint is 42*cols-0.5 by 42*rows-0.5 mm and the body
is 7*height_u mm tall, so it drops into any baseplate and stacks with any other bin."""

from blocks import gridfinity_bin

# PARAMETERS
cols = 2  # count grid units (U) in X, 42 mm each
rows = 1  # count grid units (U) in Y, 42 mm each
height_u = 3  # count height units (HU), 7 mm each
wall = 1.2  # mm side wall thickness
divisions_x = 1  # count compartments along X (1 = undivided)
divisions_y = 1  # count compartments along Y (1 = undivided)
label_tab = False  # bool, sloped label shelf on the +Y wall
scoop = False  # bool, swept quarter-round at the -Y wall
magnet_holes = False  # bool, four 6.5x2.4 mm magnet pockets per cell
screw_holes = False  # bool, four M3 screw holes per cell

result = gridfinity_bin(
    cols,
    rows,
    height_u,
    wall=wall,
    divisions_x=divisions_x,
    divisions_y=divisions_y,
    label_tab=label_tab,
    scoop=scoop,
    magnet_holes=magnet_holes,
    screw_holes=screw_holes,
)
