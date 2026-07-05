#!/usr/bin/env python3
"""Part -> unions expansion, the single place that knows a part may produce many unions.

A part (one build script) yields one or more *unions* (rigid bodies). When a part declares
a `unions` array, its script's top-level `result` is a `dict` mapping each union id to its
geometry; otherwise the part is a single union whose id is the part id. Union ids are the
namespace that `kinematics.moving_union`, plate grouping, and per-union export reference.

A part's `result` MAY also carry the reserved `KEEP_OUT_KEY` ("keep_out"), a `name ->
Workplane` mapping of author-declared keep-out zones (see `resolve_keep_out`). A zone is
never itself a union: it is excluded from every union-shaped check, export, and plate.

No CadQuery import here, so `plan_validate` (CadQuery-free) can use `iter_unions`.
"""

from collections.abc import Iterator
from typing import Any

KEEP_OUT_KEY = "keep_out"
"""Reserved `result` key for a part's declared keep-out zones. Never itself a union id."""


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
    plain Workplane is the single-union default (id = part id). The reserved `KEEP_OUT_KEY`
    entry, if present, is never a union -- it is excluded before the declared-ids comparison
    (see `resolve_keep_out` for extracting it). Raises ValueError on a declared/result
    mismatch so the caller can emit a structured error instead of a traceback.
    """
    declared = part.get("unions")
    pid = part.get("id", "(unknown)")

    if isinstance(result, dict):
        keys = [k for k in result if k != KEEP_OUT_KEY]
        declared_ids = [u["id"] for u in declared] if declared else keys
        if declared and set(keys) != set(declared_ids):
            errkeys = sorted(keys)
            raise ValueError(
                f"Part '{pid}': result keys {errkeys} do not match declared "
                f"unions {sorted(declared_ids)}"
            )
        return [(uid, result[uid]) for uid in declared_ids]

    if declared:
        raise ValueError(
            f"Part '{pid}' declares 'unions' but its result is a single Workplane, not a "
            "dict of union id -> Workplane"
        )
    return [(pid, result)]


def resolve_keep_out(part: dict, result: Any) -> list[tuple[str, Any]]:
    """Extract a part's declared keep-out zones from its script `result`.

    ``result[KEEP_OUT_KEY]``, if present, maps zone name -> Workplane; each zone name is
    itself the zone's note-to-self (same convention as a union id doubling as its
    description). Returns `[]` when the part declares no zones. Mirrors `resolve_unions`
    but for the one reserved key that is never itself a union.
    """
    if not isinstance(result, dict):
        return []
    zones = result.get(KEEP_OUT_KEY)
    if not zones:
        return []
    return list(zones.items())


def keep_out_stl_name(part_id: str, zone_name: str) -> str:
    """Filename for a declared zone's assembled-pose STL, used by both the writer
    (`model_export.export_model`) and the reader (`keep_out_check`).

    Prefixed and part-qualified so it is unambiguous in a shared STL directory and never
    collides with a real union's `<union_id>.stl`.
    """
    return f"{KEEP_OUT_KEY}__{part_id}__{zone_name}.stl"


def iter_kinematics_entries(kinematics: list[dict]) -> Iterator[dict]:
    """Flatten a kinematics forest: yield every entry at every nesting depth, depth-first.

    Each entry MAY declare `children` -- nested entries mounted on its `moving_union`. A
    top-level entry (not nested under any other entry's `children`) is mounted on the
    static frame. A child is nested directly inside its parent's JSON object, so the tree
    is acyclic by construction -- no cycle handling needed.

    Passing a single entry wrapped in a list (``iter_kinematics_entries([entry])``) yields
    that entry's own swept subtree: itself plus every descendant.
    """
    for entry in kinematics:
        yield entry
        yield from iter_kinematics_entries(entry.get("children", []))
