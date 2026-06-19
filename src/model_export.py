#!/usr/bin/env python3
"""Model-level export: assemble placed unions into a 3MF + STL artifacts.

Each part in the build plan is a union (one rigid body). This loads every part's
`result`, positions it by its `placement` into the shared assembled frame, and emits:

  1. one 3MF with each union as a separately named object carrying its `plate`
     metadata (assembled pose baked in; operator re-distributes objects to plates),
  2. one assembled-pose STL per union (the kinematic check's input),
  3. one fused STL per plate that holds more than one union (STL cannot carry
     multiple objects in fixed relative pose).

The `placement` convention is shared with the kinematic check via `placement.py`.

Usage:
    python3 model_export.py --plan BUILD_PLAN.json --parts-dir build --out dist
"""

import argparse
import json
import os
import re
import sys

import cadquery as cq

from exporters import _load_result
from exporters.threemf_multi import count_nonmanifold_edges, write_named_3mf
from placement import apply_cq

_NAME_MAX_LEN = 64


def _plate_of(part: dict) -> str:
    """Plate id for a part: explicit `plate`, else the part's own id (one per plate)."""
    return part.get("plate") or part["id"]


def _object_name(description: str, fallback: str) -> str:
    """Readable 3MF object name from a part description.

    Collapses internal whitespace/newlines to single spaces, strips control
    characters, trims, and caps length. Returns `fallback` (the part id) when the
    sanitized result is empty.
    """
    cleaned = re.sub(r"\s+", " ", description)
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned).strip()
    if len(cleaned) > _NAME_MAX_LEN:
        cleaned = cleaned[:_NAME_MAX_LEN].rstrip()
    return cleaned or fallback


def export_model(
    plan: dict,
    parts_dir: str,
    output_dir: str,
    print_orientations: dict[str, dict] | None = None,
) -> dict:
    """Export all unions to a named 3MF + per-union STL + fused-per-plate STL.

    `print_orientations` maps a part id to a placement-style orientation dict
    (`{"rotate": [...]}`, the print_orientation.py output). When supplied for a
    union, that union's deliverable 3MF object is written in the print orientation
    (ready for the bed); otherwise it falls back to the assembled pose. The
    per-union assembled-pose STLs consumed by the kinematic check are always
    written from `placement`, unaffected by the print orientation.

    Returns a dict with `model_3mf`, `union_stls` (id -> path), and `plate_stls`
    (plate -> path, only for multi-union plates).
    """
    os.makedirs(output_dir, exist_ok=True)
    parts = plan.get("parts", [])
    print_orientations = print_orientations or {}

    authored: dict[str, cq.Workplane] = {}
    placed: dict[str, cq.Workplane] = {}
    plates: dict[str, list[str]] = {}
    for part in parts:
        pid = part["id"]
        script = os.path.join(parts_dir, f"{pid}.py")
        wp = _load_result(script)
        authored[pid] = wp
        placed[pid] = apply_cq(wp, part.get("placement"))
        plates.setdefault(_plate_of(part), []).append(pid)

    # 1. named 3MF: each object in its print orientation when one is supplied,
    # else its assembled pose.
    def _deliverable(pid: str) -> cq.Workplane:
        orientation = print_orientations.get(pid)
        if orientation:
            return apply_cq(authored[pid], {"rotate": orientation.get("rotate", [])})
        return placed[pid]

    objects = [
        (
            _object_name(part.get("description", ""), part["id"]),
            _plate_of(part),
            cq.Compound.makeCompound(_deliverable(part["id"]).vals()),
        )
        for part in parts
    ]
    model_3mf = os.path.join(output_dir, "model.3mf")
    write_named_3mf(objects, model_3mf)

    # Verify the deliverable's index topology the way a slicer reads it (no
    # vertex welding on load); a non-zero count means the writer regressed.
    try:
        nonmanifold = count_nonmanifold_edges(model_3mf)
    except ImportError:
        nonmanifold = 0  # trimesh absent: skip the guard rather than fail export
    if nonmanifold:
        raise RuntimeError(
            f"{model_3mf} has {nonmanifold} non-manifold edges after export; "
            "vertex welding failed in write_named_3mf."
        )

    # 2. per-union assembled STL
    union_stls = {}
    for pid, wp in placed.items():
        stl_path = os.path.join(output_dir, f"{pid}.stl")
        cq.exporters.export(wp, stl_path)
        union_stls[pid] = stl_path

    # 3. fused STL per multi-union plate (deliverable). The cluster fuses in its
    # assembled relative poses (print-in-place), then adopts the first union's
    # print orientation so the whole plate sits on the bed as recommended.
    plate_stls = {}
    for plate, ids in plates.items():
        if len(ids) < 2:
            continue
        fused = placed[ids[0]]
        for pid in ids[1:]:
            fused = fused.union(placed[pid])
        orientation = print_orientations.get(ids[0])
        if orientation:
            fused = apply_cq(fused, {"rotate": orientation.get("rotate", [])})
        plate_path = os.path.join(output_dir, f"plate_{plate}.stl")
        cq.exporters.export(fused, plate_path)
        plate_stls[plate] = plate_path

    return {"model_3mf": model_3mf, "union_stls": union_stls, "plate_stls": plate_stls}


def main() -> None:
    parser = argparse.ArgumentParser(description="Model-level union/plate export")
    parser.add_argument("--plan", required=True, help="Path to BUILD_PLAN.json")
    parser.add_argument(
        "--parts-dir", required=True, help="Directory of <id>.py scripts"
    )
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument(
        "--orientations",
        default=None,
        help="JSON mapping part id -> orientation ({'rotate': [...]}) from "
        "print_orientation.py; deliverables are written in these poses",
    )
    args = parser.parse_args()

    plan = json.load(open(args.plan, encoding="utf-8"))
    print_orientations = None
    if args.orientations:
        print_orientations = json.load(open(args.orientations, encoding="utf-8"))
    result = export_model(plan, args.parts_dir, args.out, print_orientations)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
