"""Regenerate the golden meshes for the eval corpus.

Each builder returns the golden CadQuery solid for one part, authored in the
same frame the case's BUILD_PLAN.json describes. Run from the repo root:

    uv run python evals/generate_goldens.py [case ...]

Writes evals/cases/<case>/golden/<part_id>.stl for every (case, part).
"""

from __future__ import annotations

import sys
from pathlib import Path

import cadquery as cq

CASES_DIR = Path(__file__).parent / "cases"
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def enclosure_body():
    return cq.Workplane("XY").box(80, 50, 30).faces(">Z").shell(-2.0)


def sliding_lid():
    base = cq.Workplane("XY").box(80, 50, 2)
    lip = cq.Workplane("XY").box(74, 44, 2).translate((0, 0, 2))
    return base.union(lip)


def snap_lid():
    plate = cq.Workplane("XY").box(80, 50, 2)
    result = plate
    for x in (30, -30):
        prong = cq.Workplane("XY").box(4, 3, 4).translate((x, 0, -3))
        result = result.union(prong)
    return result


def l_bracket():
    base = cq.Workplane("XY").box(60, 40, 6, centered=(True, True, False))
    upright = cq.Workplane("XY").box(60, 6, 60, centered=(True, True, False)).translate((0, 17, 0))
    return base.union(upright)


def adapter_ring():
    flange = cq.Workplane("XY").cylinder(5, 40, centered=(True, True, False))
    tube = cq.Workplane("XY").cylinder(20, 30, centered=(True, True, False))
    return flange.union(tube).faces(">Z").workplane().hole(50)


def boss_plate():
    plate = cq.Workplane("XY").box(100, 60, 4, centered=(True, True, False))
    return (
        plate.faces(">Z")
        .workplane()
        .rect(80, 40, forConstruction=True)
        .vertices()
        .circle(4)
        .extrude(6)
    )


def wall_hook():
    profile = [(0, 0), (30, 0), (30, 20), (24, 20), (24, 6), (6, 6), (6, 60), (0, 60)]
    return cq.Workplane("XZ").polyline(profile).close().extrude(20)


def u_clip():
    profile = [(0, 0), (30, 0), (30, 4), (6, 4), (6, 21), (30, 21), (30, 25), (0, 25)]
    return cq.Workplane("XY").polyline(profile).close().extrude(15)


def phone_stand():
    profile = [(0, 0), (80, 0), (0, 70)]
    return cq.Workplane("XZ").polyline(profile).close().extrude(70)


def box_body():
    return cq.Workplane("XY").box(70, 50, 25, centered=(True, True, False)).faces(">Z").shell(-2.0)


def box_lid():
    plate = cq.Workplane("XY").box(70, 50, 3, centered=(True, True, False))
    lip = cq.Workplane("XY").box(66, 46, 2, centered=(True, True, False)).translate((0, 0, -2))
    return plate.union(lip)


def _hinged_latch_leaves():
    from blocks.joints import pin_hinge

    return pin_hinge(length=30, knuckles=3, leaf_w=20, leaf_t=4, d_filament=1.9, clearance=0.3)


def hinge_leaf_a():
    return _hinged_latch_leaves()["leaf_a"]


def hinge_leaf_b():
    return _hinged_latch_leaves()["leaf_b"]


def corrected_lid():
    plate = cq.Workplane("XY").box(70, 50, 3, centered=(True, True, False))
    lip = cq.Workplane("XY").box(66, 46, 2, centered=(True, True, False)).translate((0, 0, -2))
    return plate.union(lip)


def mount_plate():
    # Boss on the East-facing (+X) edge: right side of the South viewing
    # station per the fixed North=+Y/East=+X convention (prompts/planning.md).
    plate = cq.Workplane("XY").box(60, 40, 6, centered=(True, True, False))
    boss = (
        cq.Workplane("XY")
        .workplane(offset=6)
        .center(22, 0)
        .cylinder(8, 5, centered=(True, True, False))
    )
    return plate.union(boss)


# case name -> {part_id: builder}
GOLDENS = {
    "enclosure-body": {"enclosure_body": enclosure_body},
    "sliding-lid": {"sliding_lid": sliding_lid},
    "snap-lid": {"snap_lid": snap_lid},
    "l-bracket": {"l_bracket": l_bracket},
    "adapter-ring": {"adapter_ring": adapter_ring},
    "boss-plate": {"boss_plate": boss_plate},
    "wall-hook": {"wall_hook": wall_hook},
    "u-clip": {"u_clip": u_clip},
    "phone-stand": {"phone_stand": phone_stand},
    "two-part-box": {"box_body": box_body, "box_lid": box_lid},
    "hinged-latch": {"hinge_leaf_a": hinge_leaf_a, "hinge_leaf_b": hinge_leaf_b},
    "lid-thickness-correction": {"corrected_lid": corrected_lid},
    "east-side-mount": {"mount_plate": mount_plate},
}


def main(argv: list[str]) -> int:
    names = argv or sorted(GOLDENS)
    for name in names:
        if name not in GOLDENS:
            print(f"unknown case: {name}", file=sys.stderr)
            return 1
        out_dir = CASES_DIR / name / "golden"
        out_dir.mkdir(parents=True, exist_ok=True)
        for part_id, builder in GOLDENS[name].items():
            stl = out_dir / f"{part_id}.stl"
            cq.exporters.export(builder(), str(stl))
            print(f"wrote {stl}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
