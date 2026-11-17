"""Suggest designed-in breakaway fin placements for the overhangs of a print-pose STL.

Advisory only: reads the mesh, never edits geometry. Reuses `mesh_io.overhang_regions` (the
gate's own overhang/bridge definition). Feed each suggestion to `blocks.breakaway_fin` +
`blocks.place_fin` in the part script and export the result as a `sacrificial` union.

    python fin_placement.py part.stl --overhang-deg 45 [--bridge-max-mm 10] [--rotate JSON]

Output JSON: {success, errors, fins: [{anchor_xyz_mm, outward_xyz, height_mm, length_mm,
region_area_mm2, [build_anchor_xyz_mm, build_outward_xyz]}]}. Coordinates are in the pose the
STL is in (print pose); with `--rotate` (the accepted orientation's steps, build -> print) the
`build_*` fields give the same point/direction in the build pose the part script is authored in.
"""

import argparse
import json
import sys

MIN_FIN_HEIGHT_MM = 2.4  # blocks.supports needs 6 tine levels at 0.2 mm layers
MIN_REGION_MM2 = 4.0  # smaller overhangs (tiny-hole ceilings) are left to bridging
LENGTH_RANGE_MM = (4.0, 40.0)


def suggest_fins(mesh, overhang_deg: float, bridge_max_mm: float = 10.0) -> list[dict]:
    """One fin suggestion per non-bridge overhang region of a print-pose mesh."""
    import numpy as np

    from mesh_io import overhang_regions

    floor = float(mesh.vertices[:, 2].min())
    centroids = mesh.triangles_center
    mesh_center = mesh.bounds.mean(axis=0)
    out = []
    for region in overhang_regions(
        mesh, overhang_deg, bridge_max_mm=bridge_max_mm, exclude_bed=True
    ):
        faces = region["faces"]
        if region["bridge"] or region["area_mm2"] < MIN_REGION_MM2:
            continue
        low = faces[int(np.argmin(centroids[faces, 2]))]
        anchor = centroids[low]
        height = float(anchor[2] - floor)
        if height < MIN_FIN_HEIGHT_MM:
            continue
        w = mesh.area_faces[faces][:, None] * mesh.face_normals[faces]
        outward = np.array([w[:, 0].sum(), w[:, 1].sum(), 0.0])
        if np.linalg.norm(outward) < 1e-6:  # flat ceiling: point away from the part centre
            outward = np.array([anchor[0] - mesh_center[0], anchor[1] - mesh_center[1], 0.0])
        if np.linalg.norm(outward) < 1e-6:
            outward = np.array([1.0, 0.0, 0.0])
        outward /= np.linalg.norm(outward)
        verts = mesh.vertices[np.unique(mesh.faces[faces])]
        span = np.ptp(verts[:, :2] @ np.array([-outward[1], outward[0]]))
        length = float(min(max(span, LENGTH_RANGE_MM[0]), LENGTH_RANGE_MM[1]))
        out.append(
            {
                "anchor_xyz_mm": [round(float(c), 3) for c in anchor],
                "outward_xyz": [round(float(c), 4) for c in outward],
                "height_mm": round(height, 3),
                "length_mm": round(length, 3),
                "region_area_mm2": round(region["area_mm2"], 3),
            }
        )
    return out


def to_build_pose(fins: list[dict], rotate: list[dict]) -> list[dict]:
    """Add `build_anchor_xyz_mm` / `build_outward_xyz` by undoing the build -> print rotation."""
    import numpy as np

    from placement import to_matrix

    inv = np.linalg.inv(to_matrix({"rotate": rotate}))
    for f in fins:
        p = inv @ np.append(f["anchor_xyz_mm"], 1.0)
        d = inv[:3, :3] @ np.array(f["outward_xyz"])
        f["build_anchor_xyz_mm"] = [round(float(c), 3) for c in p[:3]]
        f["build_outward_xyz"] = [round(float(c), 4) for c in d]
    return fins


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("stl")
    ap.add_argument("--overhang-deg", type=float, default=45.0)
    ap.add_argument("--bridge-max-mm", type=float, default=10.0)
    ap.add_argument("--rotate", help="JSON rotate steps (build -> print) the STL was posed with")
    args = ap.parse_args(argv)
    result: dict = {"success": False, "errors": [], "fins": []}
    try:
        import trimesh

        mesh = trimesh.load(args.stl, force="mesh")
        fins = suggest_fins(mesh, args.overhang_deg, args.bridge_max_mm)
        if args.rotate:
            fins = to_build_pose(fins, json.loads(args.rotate))
        result.update(success=True, fins=fins)
    except Exception as exc:
        result["errors"].append({"type": "file_error", "message": str(exc), "hint": ""})
    print(json.dumps(result))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
