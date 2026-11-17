# Designed-in breakaway support fins

A fin is a thin wall standing a small gap off an overhanging face, plus horizontal one-layer
"tines" that bridge the gap and fuse into the part. The support lives in the STL, so it prints
on any slicer. Build with `blocks.breakaway_fin`, place with `blocks.place_fin`, export as its
own union with `sacrificial: true` in `BUILD_PLAN.json` (never fuse it into the part).

The quality gate emits a `fin_hint` info finding (with suggested `anchor_xyz_mm`,
`outward_xyz`, `height_mm`, `length_mm`, and `build_*` fields in the build pose) for each
overhang it flags. Opt out with `"fin_hints": false` in `BUILD_PLAN.json` `constraints`; the
gate reads the plan on every run, so the flag needs no other carrying. `src/fin_placement.py`
gives the same suggestions standalone.

## Dimensions

Source: Slant3D's published fin guidance as recorded in
[gittrahan/support-fins `docs/FIN-SPEC.md`](https://github.com/gittrahan/support-fins) (MIT).
None of this is print-tested in this repo.

| feature | value | constant |
|---|---|---|
| standoff wall to part face | 0.2 mm | `STANDOFF_MM` |
| tine height | one layer (`layer_h`, default 0.2) | `layer_h` |
| tine width | 0.4-0.8 mm | `TINE_W_MIN_MM` / `TINE_W_MAX_MM` |
| tine overlap into part | 0.2 mm | `TINE_OVERLAP_MM` |
| tine levels | 5 dense at the base (every 2nd layer), then one per 10 layers | `BASE_TINES`, `UPPER_PITCH_LAYERS` |
| wall thickness | 0.8 mm (our choice, 2 lines at 0.4) | `wall_t` |
| wall top | rounded (fillet 0.45 x wall thickness) | |
| bed pad | optional ellipse, 1 mm thick | `PAD_T_MM` |

Horizontal tines print as one continuous bead with no retraction and bend off cleanly; a
vertical tine is its own tower and is the failure mode. Not covered: resin pin mode, sway
braces for tall parts, gussets, curved/contoured walls, bed pad on tilted exports.
