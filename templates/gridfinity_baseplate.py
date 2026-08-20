"""Archetype: Gridfinity baseplate. A cols x rows grid of sockets that Gridfinity bins drop
into, 42 mm per cell so plates tile edge to edge with no gap. The default 4.75 mm thickness
is the minimal open-bottom plate; raise plate_h to leave stock under the sockets for magnets
or mounting screws."""

from blocks import gridfinity_baseplate

# PARAMETERS
cols = 3  # count grid units (U) in X, 42 mm each
rows = 2  # count grid units (U) in Y, 42 mm each
plate_h = 4.75  # mm total plate thickness (>= 7.15 to fit magnet pockets)
clearance = 0.1  # mm socket clearance around a bin foot, per side
magnet_holes = False  # bool, four 6.5x2.4 mm magnet pockets per cell
screw_holes = False  # bool, four M3 through-holes per cell for bolting the plate down

result = gridfinity_baseplate(
    cols,
    rows,
    plate_h=plate_h,
    clearance=clearance,
    magnet_holes=magnet_holes,
    screw_holes=screw_holes,
)
