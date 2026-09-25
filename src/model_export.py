#!/usr/bin/env python3
"""Model-level export: assemble placed unions into a 3MF + STL artifacts.

Each part in the build plan is a union (one rigid body). This loads every part's
`result`, positions it by its `placement` into the shared assembled frame -- or, for a
part reached via a `joints` mate chain, by its derived pose (`mate_chain.py`) instead --
and emits:

  1. one 3MF with each union as a separately named object, pre-assigned to its
     `plate` on import in Bambu Studio / OrcaSlicer (assembled pose baked in),
  2. one assembled-pose STL per union (the kinematic check's input),
  3. one fused STL per plate that holds more than one union (STL cannot carry
     multiple objects in fixed relative pose).

The `placement` convention is shared with the kinematic check via `placement.py`.

Usage:
    python3 model_export.py --plan BUILD_PLAN.json --parts-dir build --out . --stl-out stl
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

import cadquery as cq

from exporters import _load_result
from exporters.threemf_multi import count_nonmanifold_edges, write_named_3mf
from freshness import write_manifest
from mate_chain import compute_mate_poses
from placement import apply_cq, apply_matrix
from print_finishing import pose_stability_finding, uses_print_up
from units import (
    is_copy,
    keep_out_stl_name,
    keep_out_zone_key,
    load_plan,
    plate_of,
    resolve_keep_out,
    resolve_unions,
)

_NAME_MAX_LEN = 64


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


def _dedupe_object_names(records: list[tuple[str, dict]]) -> list[str]:
    """One unique 3MF object name per union, in order.

    `records` is `[(union_id, part), ...]`. Each base name is the part description
    (`_object_name`, falling back to the union id); when several unions share a base name
    -- the common case for the two unions of one multi-union part -- each colliding name is
    disambiguated by suffixing the union id (which is unique). Non-colliding names are left
    unchanged.
    """
    base_names = [_object_name(part.get("description", ""), uid) for uid, part in records]
    counts = Counter(base_names)
    return [
        f"{base} ({uid})" if counts[base] > 1 else base
        for base, (uid, _part) in zip(base_names, records, strict=True)
    ]


_MIRROR_PLANE = {"X": "YZ", "Y": "XZ", "Z": "XY"}


def load_part_unions(
    part: dict,
    parts_by_id: dict[str, dict],
    parts_dir: str,
    print_rotate: list | None = None,
) -> tuple[str, object, list[tuple[str, cq.Workplane]]]:
    """Load a part's ``(script_path, result, [(union_id, authored Workplane)])``.

    A `copy_of` part reads its source part's script (never its own), reflects the source's
    single union across the plane normal to `copy_of.mirror` when given, and returns it
    under the copy's own id. Its `result` is None: keep-out zones are not copied.

    `print_rotate` is the accepted print pose exposed to the script (see
    `exporters._load_result`); a `copy_of` part ignores it (the source is loaded pose-free).
    """
    if not is_copy(part):
        script = os.path.join(parts_dir, f"{part['id']}.py")
        result = _load_result(script, print_rotate)
        return script, result, resolve_unions(part, result)
    src = parts_by_id[part["copy_of"]["part"]]
    script = os.path.join(parts_dir, f"{src['id']}.py")
    ((_uid, wp),) = resolve_unions(src, _load_result(script))
    axis = part["copy_of"].get("mirror")
    if axis:
        wp = wp.mirror(_MIRROR_PLANE[axis])
    return script, None, [(part["id"], wp)]


def _pose_union(wp: cq.Workplane, part: dict, mate_pose: object) -> cq.Workplane:
    """Assembled-frame pose for one of a part's unions (or keep-out zones): the part's
    derived mate-chain pose when reached via a `joints` mate chain, else its `placement`.
    """
    if mate_pose is not None:
        return apply_matrix(wp, mate_pose)
    return apply_cq(wp, part.get("placement"))


def export_model(
    plan: dict,
    parts_dir: str,
    model_dir: str,
    print_orientations: dict[str, dict] | None = None,
    *,
    stl_dir: str | None = None,
) -> dict:
    """Export all unions to a named 3MF + per-union STL + fused-per-plate STL.

    `print_orientations` maps a part id to a placement-style orientation dict
    (`{"rotate": [...]}`, the print_orientation.py output). When supplied for a
    union, that union's deliverable 3MF object is written in the print orientation
    (ready for the bed); otherwise it falls back to the assembled pose. The
    per-union assembled-pose STLs consumed by the kinematic check are always
    written from `placement`, unaffected by the print orientation.

    `model_dir` is where `model.3mf` is written (the project root, so the
    deliverable 3MF sits at the top level of the working directory). `stl_dir`
    is where the STLs are written; omit it to fall back to `model_dir` (single
    combined output directory, e.g. the gate's own per-union STL directory).

    A part's script `result` may also carry the reserved `keep_out` key (a `name ->
    Workplane` mapping of declared keep-out zones, see `units.resolve_keep_out`). Each
    zone is posed the same way as its declaring part's real unions and written to its own
    assembled-pose STL (named by `units.keep_out_stl_name`) for the keep-out validation
    check to consume, but -- unlike a real union -- a zone is never written to the 3MF,
    never assigned a plate, and never included in a fused plate STL.

    Returns a dict with `model_3mf`, `union_stls` (id -> path), `plate_stls`
    (plate -> path, only for multi-union plates), `keep_out_stls`
    (`"<part_id>::<zone_name>"` -> path, only for parts that declare zones), and
    `manifest` (path to the written provenance manifest, see `freshness.write_manifest`).
    """
    os.makedirs(model_dir, exist_ok=True)
    stl_dir = stl_dir or model_dir
    os.makedirs(stl_dir, exist_ok=True)
    parts = plan.get("parts", [])
    print_orientations = print_orientations or {}
    mate_poses = compute_mate_poses(plan)  # part id -> derived 4x4 transform
    parts_by_id = {p["id"]: p for p in parts}

    # Expand each part into its unions: a part declaring `unions` returns a dict
    # {union_id: Workplane}; a plain Workplane is the single-union default (id = part id).
    authored: dict[str, cq.Workplane] = {}
    placed: dict[str, cq.Workplane] = {}
    plate_by_uid: dict[str, str] = {}
    records: list[tuple[str, dict]] = []  # (union_id, part) in order
    plates: dict[str, list[str]] = {}
    keep_out_stls: dict[str, str] = {}
    union_scripts: dict[str, tuple[str, str]] = {}  # union_id -> (part_id, script_path)
    print_rotates: dict[str, list] = {}  # union_id -> pose the finishing pass ran under
    pose_findings: list[dict] = []
    keep_out_scripts: dict[str, tuple[str, str]] = {}  # "<part_id>::<zone>" -> (part_id, path)
    for part in parts:
        rotate = None if is_copy(part) else (print_orientations.get(part["id"]) or {}).get("rotate")
        script, result, unions = load_part_unions(part, parts_by_id, parts_dir, rotate)
        declared = {u["id"]: u for u in part.get("unions", [])}
        mate_pose = mate_poses.get(part["id"])

        for uid, wp in unions:
            authored[uid] = wp
            placed[uid] = _pose_union(wp, part, mate_pose)
            plate = plate_of(part, uid, declared.get(uid))
            plate_by_uid[uid] = plate
            plates.setdefault(plate, []).append(uid)
            records.append((uid, part))
            union_scripts[uid] = (part["id"], script)
            if rotate is not None:
                print_rotates[uid] = rotate
                if uses_print_up(script) and (
                    finding := pose_stability_finding(uid, part, wp, rotate, plan)
                ):
                    pose_findings.append(finding)

        # Keep-out zones ride along with their declaring part's pose, but are never a
        # union: no 3MF object, no plate, no per-union/plate STL -- only their own
        # assembled-pose STL for the keep-out validation check.
        for zone_name, zone_wp in resolve_keep_out(part, result):
            zone_stl = os.path.join(stl_dir, keep_out_stl_name(part["id"], zone_name))
            cq.exporters.export(_pose_union(zone_wp, part, mate_pose), zone_stl)
            zone_key = keep_out_zone_key(part["id"], zone_name)
            keep_out_stls[zone_key] = zone_stl
            keep_out_scripts[zone_key] = (part["id"], script)

    # 1. named 3MF: each object in its print orientation when one is supplied,
    # else its assembled pose.
    def _deliverable(uid: str) -> cq.Workplane:
        orientation = print_orientations.get(uid)
        if orientation:
            return apply_cq(authored[uid], {"rotate": orientation.get("rotate", [])})
        return placed[uid]

    object_names = _dedupe_object_names(records)
    objects = [
        (
            name,
            plate_by_uid[uid],
            cq.Compound.makeCompound(_deliverable(uid).vals()),  # type: ignore[arg-type]
        )
        for name, (uid, _part) in zip(object_names, records, strict=True)
    ]
    model_3mf = os.path.join(model_dir, "model.3mf")
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
        stl_path = os.path.join(stl_dir, f"{pid}.stl")
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
        plate_path = os.path.join(stl_dir, f"plate_{plate}.stl")
        cq.exporters.export(fused, plate_path)
        plate_stls[plate] = plate_path

    manifest_path = write_manifest(stl_dir, union_scripts, keep_out_scripts, print_rotates)

    return {
        "model_3mf": model_3mf,
        "union_stls": union_stls,
        "plate_stls": plate_stls,
        "keep_out_stls": keep_out_stls,
        "manifest": manifest_path,
        "pose_findings": pose_findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Model-level union/plate export")
    parser.add_argument("--plan", required=True, help="Path to BUILD_PLAN.json")
    parser.add_argument("--parts-dir", required=True, help="Directory of <id>.py scripts")
    parser.add_argument("--out", required=True, help="Output directory for model.3mf")
    parser.add_argument(
        "--stl-out",
        default=None,
        help="Output directory for STLs (default: same as --out)",
    )
    parser.add_argument(
        "--orientations",
        default=None,
        help="JSON mapping part id -> orientation ({'rotate': [...]}) from "
        "print_orientation.py; deliverables are written in these poses",
    )
    args = parser.parse_args()

    plan = load_plan(args.plan)
    print_orientations = None
    if args.orientations:
        with open(args.orientations, encoding="utf-8") as f:
            print_orientations = json.load(f)
    result = export_model(plan, args.parts_dir, args.out, print_orientations, stl_dir=args.stl_out)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
