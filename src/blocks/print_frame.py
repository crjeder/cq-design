"""Print-pose awareness for part scripts.

``print_up()`` reports the print-up direction in the part's build pose, so a
script can orient pose-dependent features (teardrop peaks) without guessing the pose.
The pose comes from ``CQ_PRINT_ROTATE`` (JSON ``rotate`` list from print_orientation.py,
build -> print pose), set by the finishing run; unset means +Z, the authoring default.
"""

import json
import os

from placement import transform_direction

ENV_VAR = "CQ_PRINT_ROTATE"


def print_up() -> tuple[float, float, float]:
    """Return the print-up unit vector in the build pose (+Z when no pose is set)."""
    raw = os.environ.get(ENV_VAR)
    if not raw:
        return (0.0, 0.0, 1.0)
    # build -> print is R; print +Z in build pose is R^-1 z: undo steps in reverse.
    inverse = [{"axis": s["axis"], "angle_deg": -s["angle_deg"]} for s in reversed(json.loads(raw))]
    return transform_direction((0.0, 0.0, 1.0), {"rotate": inverse})
