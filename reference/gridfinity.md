# Gridfinity reference

Read this before authoring any part that has to interoperate with Gridfinity -- bins,
baseplates, drawer inserts, or a custom body that carries Gridfinity feet. The numbers
here are the published standard, not design choices: a part that misses them by a
millimetre is scrap, because the point of the system is that it fits parts other people
printed.

Everything below is already implemented in `blocks/gridfinity.py`. **Call the blocks;
never re-derive the profile by hand** -- the check tool (`src/gridfinity_check.py`) exists
because hand-modelled feet are the recurring failure here.

## The two modules

| Quantity | Value | Notes |
|----------|-------|-------|
| Grid pitch (1 U) | 42.0 mm | X and Y alike; baseplate cells sit on this pitch |
| Height unit (1 HU) | 7.0 mm | bin body height is a whole multiple of it |
| Inter-bin gap | 0.5 mm | a bin's footprint is `42 * u - 0.5` (41.5 mm for 1 U) |
| Baseplate footprint | `42 * u` | full pitch, so plates tile edge to edge |

A "2x1x3 bin" therefore measures 83.5 x 41.5 mm with a 21 mm body, plus the stacking lip
on top of that (see Stacking lip below for its exact built height).

## Foot profile (bin underside)

Fixed, bottom-up, from the bottom pad outward at 45 degrees:

| Step | Rise | Outward, per side |
|------|------|-------------------|
| Bottom chamfer | 0.8 mm | 0.8 mm |
| Straight band | 1.8 mm | 0 |
| Top chamfer | 2.15 mm | 2.15 mm |
| **Total** | **4.75 mm** | **2.95 mm** |

For 1 U that is a 35.6 mm bottom pad (corner radius 0.8 mm) opening to 41.5 mm at the top
(corner radius 3.75 mm). Both chamfers are 45 degrees, so the foot is self-supporting
printed bed-down -- which is also the only orientation a Gridfinity part should print in.

Above the profile the bin is solid to **7.0 mm** (the standard cavity floor): the bridge
that ties one cell's foot to the next, since neighboring feet are 0.5 mm apart at their
tops. A multi-cell bin has one foot per cell, 42 mm apart.

## Stacking lip

The lip sits on top of the body and its inner surface mirrors the foot profile, 0.35 mm
smaller per side -- that difference is the entire stacking clearance:

| Step | Rise | Inward, per side |
|------|------|------------------|
| Lower chamfer | 0.7 mm | 0.7 mm |
| Straight band | 1.8 mm | 0 |
| Upper chamfer | 1.9 mm | 1.9 mm |
| **Total** | **4.4 mm** | **2.6 mm** |

So a lipped bin measures `7 * height_u + 4.4` mm on the bed while a stack still grows by
`7 * height_u` per bin: the bin above drops into the lip. It seats 0.35 mm below the wall
top, which is why a divider or label shelf that reaches the wall top simply holds the bin
above 0.35 mm higher -- harmless, and deliberately not flagged by the check tool.

Where the wall is thinner than the lip's 2.6 mm reach, the lip needs a 45-degree support
ramp underneath it (`gridfinity_bin` adds one automatically); without it the lip's inner
tip prints in mid-air.

The standard draws two rim profiles, sharp and rounded. The sharp one ends in a knife edge
no nozzle can lay down, so `gridfinity_bin` rounds it by default (`lip_fillet=0.6`, the
value the mainstream generators use). Blunting a 45-degree wedge lowers its apex by
exactly `sqrt(2) x lip_fillet`, so a finished bin measures `7 * height_u + 3.55` rather
than the drawn `+ 4.4`. Nothing that mates moves -- `gridfinity_dimensions` reports the
as-built number, and `gridfinity_check.py` accepts either rim.

## Magnet and screw holes

| Feature | Size | Position |
|---------|------|----------|
| Magnet pocket | 6.5 mm dia x 2.4 mm deep | 26 mm apart, centered in each cell (+/-13, +/-13) |
| Screw hole | 3.0 mm (M3) | coaxial with the magnet pockets |

The pockets take 6 x 2 mm disc magnets; the extra 0.5 mm of diameter and 0.4 mm of depth
are press-fit and first-layer slop. The holes fit inside the 35.6 mm bottom pad.

## Baseplates

The socket is the negative of the foot with 0.1 mm of clearance per side (mouth 42.2 mm),
its profile 0.7 / 1.8 / 2.25 mm. The minimum plate is 4.75 mm thick and open-bottomed --
the bin's pad rests on the desk and the plate only registers it laterally. Add stock under
the sockets (`plate_h >= 7.15`) when the plate needs magnet pockets or mounting screws.

## Printing

Print bed-down, in the modelled orientation, no supports:

- both foot chamfers and the lip's support ramp are at or below the 45-degree limit
- the cavity floor bridges nothing (it sits on the solid base)
- 1.2 mm walls (3 perimeters at 0.4 mm) are the practical minimum; the standard's nominal
  1.0 mm wall is thinner than this skill's `wall_min_mm` default
- magnet pockets print as 6.5 mm bridged ceilings only if they are cut from the underside,
  which is how `gridfinity_feet` cuts them

## Blocks and tools

| Call | Use |
|------|-----|
| `gridfinity_bin(cols, rows, height_u, ...)` | complete bin; `solid=True` for a blank to cut custom pockets into |
| `gridfinity_baseplate(cols, rows, ...)` | complete baseplate |
| `gridfinity_feet(cols, rows, ...)` | just the feet, to union under a custom body (body starts at Z = 4.75) |
| `gridfinity_socket_cutter(cols, rows, ...)` | just the sockets, to cut into a custom plate/drawer/panel |
| `gridfinity_dimensions(cols, rows, height_u)` | the numbers without the geometry, for plans and mating parts |
| `gridfinity_units_for(l, w, h)` | smallest bin, in units, that holds an object of that size |
| `python src/gridfinity_check.py --script <part.py>` | conformance check: grid, height, foot profile, and mating against reference standard geometry |

## Sources

- Stu142/Gridfinity-Documentation -- dimensioned drawings of the original spec
  (baseplate, bin base, stacking lip, magnet/screw holes)
- gridfinity.xyz specification, as encoded in kennetek/gridfinity-rebuilt-openscad's
  `standard.scad` -- the profile point lists used above
- michaelgale/cq-gridfinity -- the CadQuery-side constants cross-check (grid unit,
  tolerance, hole sizes)
- Gridfinity itself is Zack Freedman's design, released for open use
