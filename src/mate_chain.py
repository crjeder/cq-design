"""Derive a mated part's assembly pose by composing its `joints` mate chain.

A matched-pair block returns both its members already expressed in one shared local
frame with exactly one physical embedding into the assembly pose. For a `joints`
entry linking member A (on a part whose world pose is already known) and member B
(on the part to derive), the two paths into that shared frame must agree:

    world_pose(A) @ dock_A  ==  world_pose(B) @ dock_B

Solving for the unknown side gives the derivation used here:

    world_pose(part_B) = world_pose(part_A) @ dock_A @ inverse(dock_B)

`plan.py`'s `_check_joints` guarantees every mated part is reachable from `root_part` and
that any extra (loop-closing) edge is a rigid joint whose `edge_residual` is within
tolerance, before this module runs. Poses come from the BFS spanning tree; closure edges
are skipped here because the part they reach already has a pose.
"""

from typing import Any


def compute_mate_poses(plan: dict) -> dict[str, Any]:
    """Return `{part_id: 4x4 transform}` for every part reached via the `joints` mate
    chain, walking outward from `root_part`. `root_part` itself is not included --
    its own `placement` (via `placement.to_matrix`) already is its pose. Empty when
    `joints` is absent or empty.
    """
    joints = plan.get("joints", [])
    if not joints:
        return {}

    import numpy as np

    from placement import to_matrix

    root_part_id = plan["root_part"]
    parts_by_id = {p["id"]: p for p in plan.get("parts", [])}
    root_pose = to_matrix(parts_by_id[root_part_id].get("placement"))

    # part_id -> list of (other_part_id, dock_here, dock_other)
    adjacency: dict[str, list[tuple[str, dict | None, dict | None]]] = {}
    for joint in joints:
        m0, m1 = joint["members"]
        adjacency.setdefault(m0["part"], []).append((m1["part"], m0.get("dock"), m1.get("dock")))
        adjacency.setdefault(m1["part"], []).append((m0["part"], m1.get("dock"), m0.get("dock")))

    poses: dict[str, Any] = {root_part_id: root_pose}
    frontier = [root_part_id]
    while frontier:
        next_frontier = []
        for pid in frontier:
            for other_id, dock_here, dock_other in adjacency.get(pid, []):
                if other_id in poses:
                    continue
                other_pose = (
                    poses[pid] @ to_matrix(dock_here) @ np.linalg.inv(to_matrix(dock_other))
                )
                poses[other_id] = other_pose
                next_frontier.append(other_id)
        frontier = next_frontier

    del poses[root_part_id]
    return poses


def edge_residual(plan: dict, poses: dict[str, Any], joint: dict) -> tuple[float, float]:
    """(translation mm, rotation deg) by which `joint`'s two docks disagree under `poses`.

    `poses` is `compute_mate_poses(plan)`; `root_part` is not in it, so its own
    placement is used. Zero for a tree edge; nonzero for a loop-closure edge whose docks
    do not compose with the rest of the ring.
    """
    import math

    import numpy as np

    from placement import to_matrix

    parts_by_id = {p["id"]: p for p in plan.get("parts", [])}

    def pose(pid: str) -> Any:
        if pid in poses:
            return poses[pid]
        return to_matrix(parts_by_id[pid].get("placement"))

    m0, m1 = joint["members"]
    a = pose(m0["part"]) @ to_matrix(m0.get("dock"))
    b = pose(m1["part"]) @ to_matrix(m1.get("dock"))
    r = np.linalg.inv(b) @ a
    cos = (np.trace(r[:3, :3]) - 1.0) / 2.0
    return float(np.linalg.norm(r[:3, 3])), math.degrees(math.acos(max(-1.0, min(1.0, cos))))
