"""Interface area between a placed tool and the body it is unioned onto (B-rep, no mesh).

The interface is min(S_b_in, S_t_in): S_b_in is the summed area of the body's faces that
lie inside (or coincide with a face of) the tool, S_t_in the same for the tool's faces
inside the body. A tool resting on a face is measured by its contact face; a tool sunk
into a face by its cross-section at that face; edge or point contact gives 0.
"""

from typing import Any

_BBOX_TOL_MM = 1e-6


def _overlaps(a, b) -> bool:
    return not (
        a.xmax < b.xmin - _BBOX_TOL_MM
        or b.xmax < a.xmin - _BBOX_TOL_MM
        or a.ymax < b.ymin - _BBOX_TOL_MM
        or b.ymax < a.ymin - _BBOX_TOL_MM
        or a.zmax < b.zmin - _BBOX_TOL_MM
        or b.zmax < a.zmin - _BBOX_TOL_MM
    )


def _faces_inside(shape: Any, other: Any) -> tuple[float, list[tuple[float, Any]]]:
    """Summed area of shape's faces inside other, with (area, centre) of each piece."""
    other_bb = other.BoundingBox()
    total, pieces = 0.0, []
    for face in shape.Faces():
        if not _overlaps(face.BoundingBox(), other_bb):
            continue
        try:
            inside = face.intersect(other)
        except Exception:  # a failed boolean on one face counts as no contact there
            continue
        for f in inside.Faces():
            area = f.Area()
            total += area
            pieces.append((area, f.Center()))
    return total, pieces


def interface_area(before: Any, tool: Any) -> tuple[float, tuple[float, float, float]]:
    """Return (area_mm2, centroid) of the interface between `tool` and `before`."""
    s_b, pieces_b = _faces_inside(before, tool)
    s_t, pieces_t = _faces_inside(tool, before)
    area, pieces = (s_b, pieces_b) if s_b <= s_t else (s_t, pieces_t)
    if area <= 0.0:
        c = tool.Center()
        return 0.0, (c.x, c.y, c.z)
    cx = sum(a * c.x for a, c in pieces) / area
    cy = sum(a * c.y for a, c in pieces) / area
    cz = sum(a * c.z for a, c in pieces) / area
    return area, (cx, cy, cz)
