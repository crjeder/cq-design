#!/usr/bin/env python3
"""Gridfinity conformance check: does this part actually fit the ecosystem?

A Gridfinity part is only useful if it interoperates with parts printed by other people:
the footprint has to land on the 42 mm grid, the body height on the 7 mm height unit, the
underside has to carry the exact stepped foot profile, and (for a baseplate) the sockets
have to accept that foot. Those are pass/fail facts about geometry, so they are checked
here rather than left to a visual review -- a bin that is 1 mm too wide looks perfect in a
preview and is scrap on the bed.

Two layers of checking, both run against the part script's own `result`:

- *measurement*: bed contact, footprint, body height, and the foot profile's width at
  three heights, read off thin cross-sections of the solid.
- *mate*: a reference solid built from `blocks.gridfinity` (the published standard) is
  seated against the part -- a bin's feet into a reference baseplate, a baseplate's
  sockets around reference feet, a stacking lip under reference feet. Any material
  overlap at the seated position means the part will not go together.

Findings use the shared quality-gate issue contract `{source, severity, type, message,
hint, ...}`. The emitted JSON adds a `detected` block naming what the part was read as
(kind, cols, rows, height units), so a misclassification is visible rather than silent.

Usage:
    python3 gridfinity_check.py --script build/bin.py
    python3 gridfinity_check.py --script build/plate.py --kind baseplate --cells 3x2
"""

import argparse
import json
import os
import sys
from typing import Any

from blocks.gridfinity import (
    BASE_PROFILE_HEIGHT_MM,
    GRID_CLEARANCE_MM,
    GRID_PITCH_MM,
    HEIGHT_UNIT_MM,
    MAGNET_HOLE_DEPTH_MM,
    STACKING_LIP_HEIGHT_MM,
    lip_height,
)
from units import make_issue

# A dimension this far off its nominal value is a real error, not modelling noise. The
# ecosystem's own fits run on 0.35 mm of clearance, so anything past a quarter millimetre
# starts eating it.
_DIM_TOL_MM = 0.25
# Cross-section heights (above the part's underside) and the foot width expected at each,
# measured relative to the footprint: the bottom pad, the straight gripping band, and the
# top of the profile.
_PROFILE_PROBES = ((0.05, -5.8), (2.0, -4.3), (BASE_PROFILE_HEIGHT_MM - 0.05, -0.1))
# Overlap below this is boolean noise on coincident faces, not real interference.
_INTERFERENCE_TOL_MM3 = 5.0
# The seated position of a foot in a lip/socket, from the profile clearance (see
# reference/gridfinity.md); probing just above it keeps mating faces from touching.
_SEAT_DROP_MM = 0.35
_SEAT_PROBE_MM = 0.05
# A lip is built either to the drawn apex or with the rim rounded off, which lowers it by
# sqrt(2) x the fillet. Both readings are legal, so both are tried before calling a height
# off-module.
_LIP_HEIGHTS_MM = (STACKING_LIP_HEIGHT_MM, lip_height())


def _slab_solids(solid: Any, z: float) -> list[Any]:
    """Separate solids of the part's cross-section at height `z` (a thin slab intersect)."""
    import cadquery as cq

    bb = solid.BoundingBox()
    span = max(bb.xlen, bb.ylen) + 10.0
    slab = (
        cq.Workplane("XY")
        .box(span, span, 0.02, centered=(True, True, False))
        .translate(((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, z))
        .val()
    )
    try:
        section = solid.intersect(slab)
    except Exception:
        return []
    return section.Solids()


def _units_from(size_mm: float, clearance: float) -> tuple[int, float]:
    """Nearest whole grid-unit count for `size_mm`, and its error in mm."""
    units = max(1, round((size_mm + clearance) / GRID_PITCH_MM))
    return units, size_mm - (units * GRID_PITCH_MM - clearance)


def _grid_error(height_mm: float) -> float:
    """Distance from `height_mm` to the nearest whole 7 mm height unit."""
    residual = height_mm % HEIGHT_UNIT_MM
    return min(residual, HEIGHT_UNIT_MM - residual)


def _classify(solid: Any, kind: str, cells: tuple[int, int] | None) -> dict:
    """Read the part as a Gridfinity object: kind, grid size, height units, lip presence."""
    bb = solid.BoundingBox()
    bin_cols, bin_err_x = _units_from(bb.xlen, GRID_CLEARANCE_MM)
    bin_rows, bin_err_y = _units_from(bb.ylen, GRID_CLEARANCE_MM)
    plate_cols, plate_err_x = _units_from(bb.xlen, 0.0)
    plate_rows, plate_err_y = _units_from(bb.ylen, 0.0)

    bin_err = max(abs(bin_err_x), abs(bin_err_y))
    plate_err = max(abs(plate_err_x), abs(plate_err_y))
    if kind == "auto":
        # A baseplate spans the full pitch and is barely thicker than the socket it holds;
        # a bin is 0.5 mm undersized and taller. Anything tall reads as a bin, so a thick
        # (weighted or screw-down) baseplate needs an explicit --kind baseplate.
        kind = "baseplate" if plate_err <= bin_err and bb.zlen <= 2 * HEIGHT_UNIT_MM else "bin"

    if kind == "baseplate":
        cols, rows = cells or (plate_cols, plate_rows)
        err = (plate_err_x, plate_err_y)
        nominal = (cols * GRID_PITCH_MM, rows * GRID_PITCH_MM)
    else:
        cols, rows = cells or (bin_cols, bin_rows)
        err = (bin_err_x, bin_err_y)
        nominal = (
            cols * GRID_PITCH_MM - GRID_CLEARANCE_MM,
            rows * GRID_PITCH_MM - GRID_CLEARANCE_MM,
        )

    # A lipped bin measures 7 x units plus the lip; a lipless one measures 7 x units.
    # Whichever reading lands closest to the height module is what the part is.
    candidates = [(_grid_error(bb.zlen), 0.0)] + [
        (_grid_error(bb.zlen - lip), lip) for lip in _LIP_HEIGHTS_MM
    ]
    _, lip = min(candidates) if kind == "bin" else (0.0, 0.0)
    stacking_lip = lip > 0.0
    body_h = bb.zlen - lip
    detected = {
        "kind": kind,
        "cols": cols,
        "rows": rows,
        "bbox_mm": [round(bb.xlen, 3), round(bb.ylen, 3), round(bb.zlen, 3)],
        "z_min_mm": round(bb.zmin, 3),
        "footprint_error_mm": [round(err[0], 3), round(err[1], 3)],
        "nominal_footprint_mm": [round(nominal[0], 3), round(nominal[1], 3)],
    }
    if kind == "bin":
        detected["body_height_mm"] = round(body_h, 3)
        detected["height_units"] = round(body_h / HEIGHT_UNIT_MM, 2)
        detected["stacking_lip"] = stacking_lip
        detected["lip_height_mm"] = round(lip, 3)
    else:
        detected["plate_height_mm"] = round(bb.zlen, 3)
    return detected


def _check_placement(part: str, det: dict) -> list[dict]:
    """Bed contact, footprint, and body height against the grid."""
    issues = []
    if abs(det["z_min_mm"]) > _DIM_TOL_MM:
        issues.append(
            make_issue(
                "gridfinity",
                "error",
                "gridfinity_bed_offset",
                f"Part '{part}': underside sits at Z={det['z_min_mm']} mm, not on the bed.",
                "Gridfinity feet print bed-down: move the geometry so its lowest face is Z=0.",
                part=part,
            )
        )

    for axis, err, nominal in zip(
        ("X", "Y"), det["footprint_error_mm"], det["nominal_footprint_mm"], strict=True
    ):
        if abs(err) > _DIM_TOL_MM:
            issues.append(
                make_issue(
                    "gridfinity",
                    "error",
                    "gridfinity_footprint",
                    f"Part '{part}': {axis} footprint is {err:+.2f} mm off the grid "
                    f"(nearest legal size {nominal} mm).",
                    f"A {det['kind']} spans "
                    + (
                        "42 x units"
                        if det["kind"] == "baseplate"
                        else "42 x units - 0.5 (the inter-bin gap)"
                    )
                    + f"; set the {axis} dimension to {nominal} mm.",
                    part=part,
                    axis=axis,
                )
            )

    if det["kind"] == "bin" and _grid_error(det["body_height_mm"]) > _DIM_TOL_MM:
        nearest = round(det["body_height_mm"] / HEIGHT_UNIT_MM) * HEIGHT_UNIT_MM
        issues.append(
            make_issue(
                "gridfinity",
                "error",
                "gridfinity_height",
                f"Part '{part}': body height {det['body_height_mm']} mm is not a whole "
                f"number of 7 mm height units (nearest {nearest:g} mm).",
                "Bins stack on the 7 mm module; set the body height to 7 x height_u "
                "(the stacking lip sits on top of that).",
                part=part,
            )
        )
    return issues


def _check_base_profile(part: str, solid: Any, det: dict) -> list[dict]:
    """Foot-profile widths at three heights, and one foot per grid cell."""
    if det["kind"] != "bin":
        return []
    issues = []
    footprint = det["nominal_footprint_mm"]
    for height, delta in _PROFILE_PROBES:
        sections = _slab_solids(solid, det["z_min_mm"] + height)
        if not sections:
            issues.append(
                make_issue(
                    "gridfinity",
                    "error",
                    "gridfinity_base_profile",
                    f"Part '{part}': no material {height} mm above the underside.",
                    "The bottom 4.75 mm must be the stepped Gridfinity foot; build it with "
                    "gridfinity_feet() or gridfinity_bin().",
                    part=part,
                    probe_height_mm=height,
                )
            )
            continue
        boxes = [s.BoundingBox() for s in sections]
        spans = (
            max(b.xmax for b in boxes) - min(b.xmin for b in boxes),
            max(b.ymax for b in boxes) - min(b.ymin for b in boxes),
        )
        for axis, measured, nominal in zip(("X", "Y"), spans, footprint, strict=True):
            expected = nominal + delta
            if abs(measured - expected) > _DIM_TOL_MM:
                issues.append(
                    make_issue(
                        "gridfinity",
                        "error",
                        "gridfinity_base_profile",
                        f"Part '{part}': at {height} mm above the underside the foot measures "
                        f"{measured:.2f} mm in {axis}, not the {expected:.2f} mm the standard "
                        "profile gives.",
                        "The foot profile is fixed: 0.8 mm chamfer, 1.8 mm straight, 2.15 mm "
                        "chamfer. Use gridfinity_feet() rather than hand-modelling it.",
                        part=part,
                        probe_height_mm=height,
                        axis=axis,
                        measured_mm=round(measured, 3),
                        expected_mm=round(expected, 3),
                    )
                )

        if height < 1.0:
            expected_feet = det["cols"] * det["rows"]
            if len(sections) != expected_feet:
                issues.append(
                    make_issue(
                        "gridfinity",
                        "warning",
                        "gridfinity_base_profile",
                        f"Part '{part}': {len(sections)} separate foot pad(s) at the "
                        f"underside, expected {expected_feet} for a "
                        f"{det['cols']}x{det['rows']} part.",
                        "Every grid cell carries its own foot, 42 mm apart, joined only "
                        "above the profile.",
                        part=part,
                        pads=len(sections),
                        expected_pads=expected_feet,
                    )
                )
    return issues


def _above(solid: Any, z: float) -> Any:
    """The part of `solid` above height `z`."""
    import cadquery as cq

    bb = solid.BoundingBox()
    span = max(bb.xlen, bb.ylen) + 10.0
    keep = (
        cq.Workplane("XY")
        .box(span, span, bb.zmax - z + 1.0, centered=(True, True, False))
        .translate(((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, z))
        .val()
    )
    return solid.intersect(keep)


def _seats(part_solid: Any, reference: Any, offset: tuple[float, float, float]) -> float:
    """Overlap volume in mm^3 with `reference` moved to `offset` against the part.

    Zero (within tolerance) means the two go together at that position; anything more is
    material the printer would have to put in the same place twice.
    """
    import cadquery as cq

    moved = reference.moved(cq.Location(cq.Vector(*offset)))
    try:
        overlap = part_solid.intersect(moved)
    except Exception:
        return 0.0
    return overlap.Volume() if overlap is not None else 0.0


def _check_mates(part: str, solid: Any, det: dict) -> list[dict]:
    """Seat reference standard geometry against the part and look for interference.

    The reference is built from `blocks.gridfinity`, so this asks the only question that
    matters in the end: would this part go together with someone else's?
    """
    from blocks.gridfinity import gridfinity_baseplate, gridfinity_feet

    issues = []
    cols, rows = det["cols"], det["rows"]
    bb = solid.BoundingBox()
    # Reference geometry is centered on the origin; the part need not be.
    dx, dy = (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2
    # Seat the reference a hair clear of contact so touching faces are not "interference".
    seat = _SEAT_DROP_MM - _SEAT_PROBE_MM

    if det["kind"] == "bin":
        # A standard baseplate slid up under the part's feet.
        plate_h = BASE_PROFILE_HEIGHT_MM + MAGNET_HOLE_DEPTH_MM
        plate = gridfinity_baseplate(cols, rows, plate_h=plate_h).val()
        plate_z = bb.zmin - (plate_h - BASE_PROFILE_HEIGHT_MM + seat)
        overlap = _seats(solid, plate, (dx, dy, plate_z))
        if overlap > _INTERFERENCE_TOL_MM3:
            issues.append(
                make_issue(
                    "gridfinity",
                    "error",
                    "gridfinity_mate",
                    f"Part '{part}': its feet overlap a standard baseplate by "
                    f"{overlap:.1f} mm^3 when seated -- it will not drop into a grid.",
                    "Rebuild the underside with gridfinity_feet()/gridfinity_bin() instead "
                    "of adjusting the profile by hand.",
                    part=part,
                    overlap_mm3=round(overlap, 2),
                )
            )
        if det["stacking_lip"]:
            # The feet of the bin that would stack on top of this one. Only the lip itself
            # is in question, so the part is clipped to the material above the body: a
            # divider or label shelf that reaches the wall top just holds the bin above
            # 0.35 mm higher, it does not stop the stack.
            feet = gridfinity_feet(cols, rows).val()
            lip_only = _above(solid, bb.zmin + det["body_height_mm"])
            overlap = _seats(lip_only, feet, (dx, dy, bb.zmin + det["body_height_mm"] - seat))
            if overlap > _INTERFERENCE_TOL_MM3:
                issues.append(
                    make_issue(
                        "gridfinity",
                        "error",
                        "gridfinity_mate",
                        f"Part '{part}': the stacking lip overlaps the feet of a bin placed "
                        f"on top by {overlap:.1f} mm^3 -- bins will not stack.",
                        "The lip recess mirrors the foot profile (0.7 / 1.8 / 1.9 mm); build "
                        "it with gridfinity_bin(stacking_lip=True).",
                        part=part,
                        overlap_mm3=round(overlap, 2),
                    )
                )
    else:
        # Standard bin feet dropped into the part's sockets.
        feet = gridfinity_feet(cols, rows).val()
        overlap = _seats(solid, feet, (dx, dy, bb.zmax - BASE_PROFILE_HEIGHT_MM + seat))
        if overlap > _INTERFERENCE_TOL_MM3:
            issues.append(
                make_issue(
                    "gridfinity",
                    "error",
                    "gridfinity_mate",
                    f"Part '{part}': its sockets overlap standard bin feet by "
                    f"{overlap:.1f} mm^3 -- bins will not seat in this baseplate.",
                    "Cut the sockets with gridfinity_socket_cutter() (or use "
                    "gridfinity_baseplate()) so the mouth and profile match the standard.",
                    part=part,
                    overlap_mm3=round(overlap, 2),
                )
            )
    return issues


def run_gridfinity_check(
    script_path: str, kind: str = "auto", cells: tuple[int, int] | None = None
) -> tuple[list[dict], dict]:
    """Check the part script's geometry against the Gridfinity standard.

    Returns ``(issues, detected)``. `detected` records how the part was read (kind, grid
    size, height units); it is empty when the script could not be loaded, in which case
    the single issue is `check_skipped`.
    """
    try:
        from exporters import _load_result

        result = _load_result(script_path)
    except Exception as exc:  # the wrapper reports script failures; never double-report
        return [
            make_issue(
                "gridfinity",
                "warning",
                "check_skipped",
                f"Could not load '{script_path}' to check it: {exc}",
                "Fix the part script first; the Gridfinity check re-runs it to measure the "
                "geometry.",
                script=script_path,
            )
        ], {}

    workplanes = result.items() if isinstance(result, dict) else [(None, result)]
    stem = os.path.splitext(os.path.basename(script_path))[0]

    issues: list[dict] = []
    detected: dict = {}
    for union_id, workplane in workplanes:
        solids: list[Any] = workplane.vals() if hasattr(workplane, "vals") else [workplane]
        solids = [s for s in solids if hasattr(s, "BoundingBox")]
        if not solids:
            continue
        solid = solids[0]
        for extra in solids[1:]:
            solid = solid.fuse(extra)
        name = f"{stem}:{union_id}" if union_id else stem

        det = _classify(solid, kind, cells)
        detected[name] = det
        issues.extend(_check_placement(name, det))
        issues.extend(_check_base_profile(name, solid, det))
        issues.extend(_check_mates(name, solid, det))
    return issues, detected


def _parse_cells(value: str) -> tuple[int, int]:
    try:
        cols, rows = (int(part) for part in value.lower().split("x", 1))
    except ValueError:
        raise argparse.ArgumentTypeError(f"--cells expects COLSxROWS, got {value!r}") from None
    if cols < 1 or rows < 1:
        raise argparse.ArgumentTypeError(f"--cells must be positive, got {value!r}")
    return cols, rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Gridfinity standard conformance check")
    parser.add_argument("--script", required=True, help="Path to the part script to check")
    parser.add_argument(
        "--kind",
        choices=("auto", "bin", "baseplate"),
        default="auto",
        help="What the part is meant to be (default: read it from the geometry)",
    )
    parser.add_argument(
        "--cells",
        type=_parse_cells,
        help="Intended grid size as COLSxROWS (default: read it from the footprint)",
    )
    args = parser.parse_args()

    issues, detected = run_gridfinity_check(args.script, args.kind, args.cells)
    print(json.dumps({"issues": issues, "detected": detected}, indent=2))
    sys.exit(1 if any(i["severity"] == "error" for i in issues) else 0)


if __name__ == "__main__":
    main()
