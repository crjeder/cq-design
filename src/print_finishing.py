"""Print-pose finishing helpers: orientation scoring and the pose-stability guard.

A part script that calls ``blocks.print_up()`` produces different geometry once the accepted
print pose is known (``CQ_PRINT_ROTATE``, see ``exporters._load_result``). ``write_assembly``
re-loads each script under that pose; ``pose_stability_finding`` then re-scores orientation
on the finished solid and reports when the optimizer would now pick a different pose.
"""

import os
import tempfile

import cadquery as cq
import numpy as np

from mesh_io import load_mesh
from placement import to_matrix
from print_orientation import optimize_orientation


def orientation_for(
    result: cq.Workplane,
    part: dict,
    overhang_deg: float,
    optimize_for: str,
    bridge_max_mm: float = 10.0,
) -> dict:
    """Recommended print orientation for one union's authored geometry.

    `optimize_orientation` scores a mesh in its authored frame, so the result is
    exported to a throwaway STL and reloaded. Uses the part's declared `load.dir` /
    `load.type` / `show_face.dir` when present (the optimizer infers direction
    otherwise and defaults type to `tension`) and the effective `optimize_for` mode
    resolved from the plan.
    """
    load = part.get("load")
    load_dir = load["dir"] if load else None
    load_type = load.get("type", "tension") if load else "tension"
    show_face = part.get("show_face")
    show_dir = show_face["dir"] if show_face else None
    with tempfile.TemporaryDirectory() as tmp:
        stl = os.path.join(tmp, "authored.stl")
        cq.exporters.export(result, stl)
        mesh = load_mesh(stl)
    return optimize_orientation(
        mesh,
        overhang_deg,
        load_dir,
        optimize_for=optimize_for,
        show_face=show_dir,
        load_type=load_type,
        bridge_max_mm=bridge_max_mm,
    )


def uses_print_up(script_path: str) -> bool:
    """True when the part script references `print_up` (its geometry depends on the pose)."""
    with open(script_path, encoding="utf-8") as f:
        return "print_up" in f.read()


def pose_stability_finding(
    uid: str, part: dict, finished: cq.Workplane, accepted_rotate: list, plan: dict
) -> dict | None:
    """Advisory issue when re-scoring the finished solid picks a different pose, else None.

    The accepted pose is kept either way; this only reports the shift.
    """
    constraints = plan["constraints"]
    chosen = orientation_for(
        finished,
        part,
        constraints["overhang_max_deg"],
        part.get("optimize_for", plan.get("optimize_for", "strength")),
        constraints.get("bridge_max_mm", 10.0),
    )
    if np.allclose(to_matrix({"rotate": chosen["rotate"]}), to_matrix({"rotate": accepted_rotate})):
        return None
    return {
        "source": "finishing",
        "severity": "warning",
        "type": "pose_shift",
        "message": (
            f"Union '{uid}': after the print-finishing pass the optimizer prefers "
            f"{chosen['rotate']} over the accepted {accepted_rotate}; the accepted pose is kept."
        ),
        "hint": "Re-run print orientation on the finished geometry if the new pose is better.",
        "union": uid,
    }
