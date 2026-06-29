#!/usr/bin/env python3
"""Part -> unions expansion, the single place that knows a part may produce many unions.

A part (one build script) yields one or more *unions* (rigid bodies). When a part declares
a `unions` array, its script's top-level `result` is a `dict` mapping each union id to its
geometry; otherwise the part is a single union whose id is the part id. Union ids are the
namespace that `kinematics.moving_union`, plate grouping, and per-union export reference.

No CadQuery import here, so `plan_validate` (CadQuery-free) can use `iter_unions`.
"""

from typing import Any


def plate_of(part: dict, union_id: str, union: dict | None = None) -> str:
    """Plate for a union: its own `plate`, else the part's `plate`, else the union id."""
    if union is not None and union.get("plate"):
        return union["plate"]
    return part.get("plate") or union_id


def iter_unions(plan: dict) -> list[tuple[dict, str, str]]:
    """Expand every part into its unions: ``(part, union_id, plate)`` in plan order.

    A part with a `unions` array yields one tuple per declared union; a part without yields a
    single union whose id is the part id (today's default).
    """
    out: list[tuple[dict, str, str]] = []
    for part in plan.get("parts", []):
        declared = part.get("unions")
        if declared:
            for u in declared:
                uid = u["id"]
                out.append((part, uid, plate_of(part, uid, u)))
        else:
            pid = part["id"]
            out.append((part, pid, plate_of(part, pid)))
    return out


def resolve_unions(part: dict, result: Any) -> list[tuple[str, Any]]:
    """Normalize a script's `result` into ``[(union_id, workplane), ...]`` for the part.

    A `dict` result maps declared union ids to geometry (keys must equal the declared ids); a
    plain Workplane is the single-union default (id = part id). Raises ValueError on a
    declared/result mismatch so the caller can emit a structured error instead of a traceback.
    """
    declared = part.get("unions")
    pid = part.get("id", "(unknown)")

    if isinstance(result, dict):
        keys = set(result.keys())
        declared_ids = [u["id"] for u in declared] if declared else list(result.keys())
        if declared and keys != set(declared_ids):
            raise ValueError(
                f"Part '{pid}': result keys {sorted(keys)} do not match declared "
                f"unions {sorted(declared_ids)}"
            )
        return [(uid, result[uid]) for uid in declared_ids]

    if declared:
        raise ValueError(
            f"Part '{pid}' declares 'unions' but its result is a single Workplane, not a "
            "dict of union id -> Workplane"
        )
    return [(pid, result)]
