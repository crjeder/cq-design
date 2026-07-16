# Hardware dimension reference

Use these tables when choosing parameters for `heat_set_boss`, `counterbore_hole`, `countersink_hole`, and `hex_nut_trap`.

## Heat-set inserts (CNC Kitchen / Hilitchi-style)

| Size | Insert OD (mm) | Insert length (mm) | Boss OD rec. (mm) | Hole dia. for PLA (mm) |
|------|---------------|-------------------|-------------------|------------------------|
| M2   | 3.2           | 4.0               | 6.0               | 3.0                    |
| M2.5 | 3.5           | 4.0               | 6.5               | 3.3                    |
| M3   | 4.6           | 5.7               | 7.5               | 4.4                    |
| M4   | 5.6           | 8.1               | 9.0               | 5.4                    |
| M5   | 6.4           | 9.5               | 10.5              | 6.2                    |

Pass `size='Mx-pitch-length'` to `heat_set_boss` (e.g. `'M3-0.5-6'`). The hole dia. column
is the hole sized for a firm heat-press fit in PLA; PETG may need +0.1 mm.

## Socket head cap screws (ISO 4762 / DIN 912)

For `counterbore_hole(d_screw, d_head, h_head, depth)`:

| Size | d_screw clearance (mm) | d_head (mm) | h_head (mm) |
|------|------------------------|-------------|-------------|
| M2   | 2.4                    | 3.8         | 2.0         |
| M2.5 | 2.9                    | 4.5         | 2.5         |
| M3   | 3.4                    | 5.5         | 3.0         |
| M4   | 4.5                    | 7.0         | 4.0         |
| M5   | 5.5                    | 8.5         | 5.0         |
| M6   | 6.6                    | 10.0        | 6.0         |

## Flat-head screws, 90 deg countersink (DIN 7991 / ISO 10642)

For `countersink_hole(d_screw, d_sink, depth, angle=90)`:

| Size | d_screw clearance (mm) | d_sink (mm) |
|------|------------------------|-------------|
| M3   | 3.2                    | 6.0         |
| M4   | 4.3                    | 8.0         |
| M5   | 5.3                    | 10.0        |
| M6   | 6.4                    | 12.0        |

## Hex nuts (ISO 4032 / DIN 934)

For `hex_nut_trap(nut_flat, nut_h, depth, d_screw=0)`:

| Size | nut_flat (mm) | nut_h (mm) | d_screw clearance (mm) |
|------|--------------|------------|------------------------|
| M2   | 4.0          | 1.6        | 2.4                    |
| M2.5 | 5.0          | 2.0        | 2.9                    |
| M3   | 5.5          | 2.4        | 3.4                    |
| M4   | 7.0          | 3.2        | 4.5                    |
| M5   | 8.0          | 4.7        | 5.5                    |
| M6   | 10.0         | 5.2        | 6.6                    |

Add 0.3-0.5 mm to `nut_flat` for a pocket that doesn't require force-fitting in PLA.
