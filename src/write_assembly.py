#!/usr/bin/env python3
"""Write the assembly: the assembled-pose STLs the whole-model checks consume.

Each part in the build plan is a union (one rigid body). This loads every part's
`result`, positions it by its `placement` into the shared assembled frame -- or, for a
part reached via a `joints` mate chain, by its derived pose (`mate_chain.py`) instead --
and writes, into one directory:

  1. one assembled-pose STL per union (the kinematic / plate-clearance checks' input),
  2. one assembled-pose STL per declared keep-out zone,
  3. the provenance manifest (`freshness.write_manifest`).

It writes nothing user-facing: `model.3mf`, plate STLs and STEP/OBJ/IGES/SCAD come from
`build/build.py` (`deliverables.py`), which reuses `assemble()` below.

The `placement` convention is shared with the kinematic check via `placement.py`.

Usage:
    python3 write_assembly.py --plan BUILD_PLAN.json --parts-dir build --out stl \
        [--orientations build/orientations.json]
"""

import argparse
import json
import os
import sys
from collections.abc import Callable

import cadquery as cq

from exporters import _load_result
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
    read_json,
    resolve_keep_out,
    resolve_unions,
)

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


def pose_union(wp: cq.Workplane, part: dict, mate_pose: object) -> cq.Workplane:
    """Assembled-frame pose for one of a part's unions (or keep-out zones): the part's
    derived mate-chain pose when reached via a `joints` mate chain, else its `placement`.
    """
    if mate_pose is not None:
        return apply_matrix(wp, mate_pose)
    return apply_cq(wp, part.get("placement"))


def assemble(
    plan: dict,
    parts_dir: str,
    print_orientations: dict[str, dict] | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Load every part and pose its unions and keep-out zones in the assembled frame.

    `print_orientations` maps a part id to a placement-style orientation dict
    (`{"rotate": [...]}`); a part's script sees it as its finishing pose (see
    `exporters._load_result`). Returns a dict with:

    - `authored`: union id -> Workplane in the part frame
    - `placed`: union id -> Workplane in the assembled pose
    - `records`: `[(union_id, part)]` in plan order
    - `plate_by_uid` / `plates`: plate of each union, and plate -> union ids
    - `zones`: `"<part_id>::<zone>"` -> (part_id, zone_name, posed keep-out Workplane)
    - `union_scripts` / `keep_out_scripts`: id -> (part_id, script path), for the manifest
    - `print_rotates`: union id -> pose the finishing pass ran under
    - `pose_findings`: advisory `pose_shift` findings

    `progress`, when given, is called with a `[k/N] loading <part_id>` line per part.
    """
    parts = plan.get("parts", [])
    print_orientations = print_orientations or {}
    mate_poses = compute_mate_poses(plan)  # part id -> derived 4x4 transform
    parts_by_id = {p["id"]: p for p in parts}
    report = progress or (lambda _line: None)

    asm: dict = {
        "authored": {},
        "placed": {},
        "records": [],
        "plate_by_uid": {},
        "plates": {},
        "zones": {},
        "union_scripts": {},
        "keep_out_scripts": {},
        "print_rotates": {},
        "pose_findings": [],
    }
    for k, part in enumerate(parts, 1):
        report(f"[{k}/{len(parts)}] loading {part['id']}")
        rotate = None if is_copy(part) else (print_orientations.get(part["id"]) or {}).get("rotate")
        script, result, unions = load_part_unions(part, parts_by_id, parts_dir, rotate)
        declared = {u["id"]: u for u in part.get("unions", [])}
        mate_pose = mate_poses.get(part["id"])

        for uid, wp in unions:
            asm["authored"][uid] = wp
            asm["placed"][uid] = pose_union(wp, part, mate_pose)
            plate = plate_of(part, uid, declared.get(uid))
            asm["plate_by_uid"][uid] = plate
            asm["plates"].setdefault(plate, []).append(uid)
            asm["records"].append((uid, part))
            asm["union_scripts"][uid] = (part["id"], script)
            if rotate is not None:
                asm["print_rotates"][uid] = rotate
                if uses_print_up(script) and (
                    finding := pose_stability_finding(uid, part, wp, rotate, plan)
                ):
                    asm["pose_findings"].append(finding)

        # Keep-out zones ride along with their declaring part's pose but are never a
        # union: no plate and no user-facing file, only their own assembled-pose STL.
        for zone_name, zone_wp in resolve_keep_out(part, result):
            zone_key = keep_out_zone_key(part["id"], zone_name)
            asm["zones"][zone_key] = (part["id"], zone_name, pose_union(zone_wp, part, mate_pose))
            asm["keep_out_scripts"][zone_key] = (part["id"], script)
    return asm


def write_assembly(
    plan: dict,
    parts_dir: str,
    stl_dir: str,
    print_orientations: dict[str, dict] | None = None,
    *,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Write the assembled-pose STL per union and per keep-out zone, plus the manifest.

    The per-union STLs are always in the assembled `placement` pose, unaffected by any
    print orientation (which only drives the finishing pass and the manifest's
    `print_rotate`). Keep-out STLs are named by `units.keep_out_stl_name`.

    Returns a dict with `union_stls` (id -> path), `keep_out_stls`
    (`"<part_id>::<zone_name>"` -> path), `manifest` (path, see `freshness.write_manifest`)
    and `pose_findings`. `progress` also receives a `[k/N] stl <union_id>` line per STL; it
    never affects the files written or the returned dict.
    """
    os.makedirs(stl_dir, exist_ok=True)
    asm = assemble(plan, parts_dir, print_orientations, progress)
    report = progress or (lambda _line: None)

    keep_out_stls = {}
    for zone_key, (part_id, zone_name, zone_wp) in asm["zones"].items():
        zone_stl = os.path.join(stl_dir, keep_out_stl_name(part_id, zone_name))
        cq.exporters.export(zone_wp, zone_stl)
        keep_out_stls[zone_key] = zone_stl

    union_stls = {}
    for k, (uid, wp) in enumerate(asm["placed"].items(), 1):
        report(f"[{k}/{len(asm['placed'])}] stl {uid}")
        stl_path = os.path.join(stl_dir, f"{uid}.stl")
        cq.exporters.export(wp, stl_path)
        union_stls[uid] = stl_path

    manifest_path = write_manifest(
        stl_dir, asm["union_scripts"], asm["keep_out_scripts"], asm["print_rotates"]
    )
    return {
        "union_stls": union_stls,
        "keep_out_stls": keep_out_stls,
        "manifest": manifest_path,
        "pose_findings": asm["pose_findings"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the assembled-pose STLs and manifest")
    parser.add_argument("--plan", required=True, help="Path to BUILD_PLAN.json")
    parser.add_argument("--parts-dir", required=True, help="Directory of <id>.py scripts")
    parser.add_argument("--out", required=True, help="Output directory for the STLs and manifest")
    parser.add_argument(
        "--orientations",
        default=None,
        help="JSON mapping part id -> orientation ({'rotate': [...]}) from "
        "print_orientation.py; part scripts see it as their finishing pose",
    )
    args = parser.parse_args()

    plan = load_plan(args.plan)
    print_orientations = None
    if args.orientations:
        print_orientations = read_json(args.orientations, "orientations file")
    result = write_assembly(plan, args.parts_dir, args.out, print_orientations)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
