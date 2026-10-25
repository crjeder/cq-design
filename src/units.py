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

import argparse
import json
import math
import os
import re
import sys
from collections.abc import Callable, Iterator
from typing import Any

KEEP_OUT_KEY = "keep_out"
"""Reserved `result` key for a part's declared keep-out zones. Never itself a union id."""


class InputFileError(SystemExit):
    """An input file is missing, unreadable, or not valid JSON. A SystemExit subclass so an
    uncaught one prints `error: <message>` to stderr and exits 1 with no traceback; JSON-contract
    scripts catch it and report a `file_error` instead."""

    def __init__(self, message: str):
        super().__init__(f"error: {message}")
        self.message = message


def read_json(path: str, role: str) -> Any:
    """Parse the JSON file at `path`; `role` names it in errors (e.g. "BUILD_PLAN.json")."""
    if os.path.isdir(path):  # open() raises PermissionError for a directory on Windows
        raise InputFileError(f"{role} is a directory, expected a file: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise InputFileError(f"{role} not found: {path}") from None
    except OSError as e:
        raise InputFileError(f"cannot read {role} {path}: {e.strerror or e}") from None
    except json.JSONDecodeError as e:
        raise InputFileError(
            f"{role} {path} is not valid JSON (line {e.lineno}, col {e.colno}): {e.msg}"
        ) from None


def load_plan(path: str) -> dict:
    """Load and parse a BUILD_PLAN.json-shaped file. Shared by every CLI entry point that
    takes a `--plan` argument."""
    return read_json(path, "BUILD_PLAN.json")


def add_plan_argument(parser: argparse.ArgumentParser) -> None:
    """Add the `--plan` argument shared by every check-stage CLI entry point."""
    parser.add_argument("--plan", required=True, help="Path to BUILD_PLAN.json")


def add_stl_dir_argument(parser: argparse.ArgumentParser, help: str) -> None:
    """Add the `--stl-dir` argument shared by the STL-comparing check-stage CLIs
    (`keep_out_check`, `plate_clearance_check`, `kinematic_check`), each with its own
    stage-specific `help` text."""
    parser.add_argument("--stl-dir", required=True, help=help)


def add_parts_dir_argument(parser: argparse.ArgumentParser) -> None:
    """Add the optional `--parts-dir` argument shared by the STL-comparing check-stage CLIs,
    enabling the stale-export freshness check against the current part scripts. Omitting it
    degrades that check to `check_skipped` rather than blocking the rest of the stage."""
    parser.add_argument(
        "--parts-dir",
        default=None,
        help="Directory of current <part_id>.py scripts, to detect an exported STL that is "
        "stale relative to its source script (omit to skip the freshness check)",
    )


def emit_issues(issues: list[dict], *, fail_on_error: bool = True) -> None:
    """Print `{"issues": issues}` and exit. Shared CLI tail for every check stage that
    reports the quality-gate issue contract: exit 1 if any issue is `severity: "error"`
    and `fail_on_error` (the default), else exit 0."""
    print(json.dumps({"issues": issues}, indent=2))
    if not fail_on_error:
        sys.exit(0)
    has_error = any(i["severity"] == "error" for i in issues)
    sys.exit(1 if has_error else 0)


def run_stl_dir_check_cli(
    description: str, stl_dir_help: str, check_fn: Callable[..., list[dict]]
) -> None:
    """Shared CLI entry point for a check stage taking `--plan`/`--stl-dir`/`--parts-dir` and
    calling `check_fn(plan, stl_dir, parts_dir=parts_dir)` -- the common shape of
    `keep_out_check.main` and `plate_clearance_check.main`."""
    parser = argparse.ArgumentParser(description=description)
    add_plan_argument(parser)
    add_stl_dir_argument(parser, stl_dir_help)
    add_parts_dir_argument(parser)
    args = parser.parse_args()

    plan = load_plan(args.plan)
    issues = check_fn(plan, args.stl_dir, parts_dir=args.parts_dir)
    emit_issues(issues)


def make_issue(
    source: str, severity: str, type_: str, message: str, hint: str, **extra: Any
) -> dict:
    """Build a finding in the shared quality-gate issue contract `{source, severity, type,
    message, hint, ...}`, used by every whole-model check stage (`kinematic_check`,
    `plate_clearance_check`, `keep_out_check`)."""
    issue = {
        "source": source,
        "severity": severity,
        "type": type_,
        "message": message,
        "hint": hint,
    }
    issue.update(extra)
    return issue


def stl_path(stl_dir: str, union_id: str) -> str:
    """Assembled-pose STL path for a union/part id: the naming convention `write_assembly.py`
    writes and every whole-model check stage reads."""
    return os.path.join(stl_dir, f"{union_id}.stl")


def bbox_envelope(
    shapes: list[Any],
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Build-pose (lo, hi) bbox enveloping every CadQuery shape/solid in `shapes`, or
    None if none have a usable `.BoundingBox()`. Shared by `edge_treatment_check` and
    `feature_presence_check`, which construction-time-hook fillet/chamfer/cut/union to
    record positioned features and need the same min/max accumulation over their solids."""
    lo = [math.inf, math.inf, math.inf]
    hi = [-math.inf, -math.inf, -math.inf]
    for shape in shapes:
        try:
            bb = shape.BoundingBox()
        except Exception:
            continue
        lo = [min(lo[0], bb.xmin), min(lo[1], bb.ymin), min(lo[2], bb.zmin)]
        hi = [max(hi[0], bb.xmax), max(hi[1], bb.ymax), max(hi[2], bb.zmax)]
    if lo[0] == math.inf:
        return None
    return (lo[0], lo[1], lo[2]), (hi[0], hi[1], hi[2])


def plate_of(part: dict, union_id: str, union: dict | None = None) -> str:
    """Plate for a union: its own `plate`, else the part's `plate`, else the union id."""
    if union is not None and union.get("plate"):
        return union["plate"]
    return part.get("plate") or union_id


_DEFAULT_COLORS = {
    "PLA": "#D9D9D9",
    "PETG": "#9FC5E8",
    "ABS": "#E6E6E6",
    "ASA": "#CFCFCF",
    "TPU": "#222222",
    "PA": "#F3E5AB",
    "PC": "#F2F2F2",
    "PVA": "#FFE599",
    "HIPS": "#F9F9F9",
}


def material_of(plan: dict, part: dict, union: dict | None = None) -> str:
    """Material for a union: its own `material`, else the part's, else the plan's."""
    return (union or {}).get("material") or part.get("material") or plan.get("material", "PLA")


def color_of(plan: dict, part: dict, union: dict | None = None) -> str:
    """Color for a union: its own `color`, else the part's, else one derived from its material."""
    return (
        (union or {}).get("color")
        or part.get("color")
        or _DEFAULT_COLORS.get(material_of(plan, part, union), "#D9D9D9")
    ).upper()


def union_materials(plan: dict) -> dict[str, tuple[str, str]]:
    """Union id -> ``(material, color)`` in plan order."""
    out: dict[str, tuple[str, str]] = {}
    for part in plan.get("parts", []):
        for u in part.get("unions") or [None]:
            uid = u["id"] if u else part["id"]
            out[uid] = (material_of(plan, part, u), color_of(plan, part, u))
    return out


def assign_slots(plan: dict) -> dict[str, int]:
    """Union id -> 1-based filament slot; distinct (material, color) pairs are numbered in
    order of first appearance."""
    slots: dict[tuple[str, str], int] = {}
    return {
        uid: slots.setdefault(pair, len(slots) + 1) for uid, pair in union_materials(plan).items()
    }


def is_copy(part: dict) -> bool:
    """True when the part is declared `copy_of` another part (no script of its own)."""
    return bool(part.get("copy_of"))


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


def _sanitize_zone_name(zone_name: str) -> str:
    """Author-supplied zone names are not filename-safe; collapse to `[A-Za-z0-9_-]`."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", zone_name)


def keep_out_stl_name(part_id: str, zone_name: str) -> str:
    """Filename for a declared zone's assembled-pose STL, used by both the writer
    (`write_assembly.assemble`) and the reader (`keep_out_check`).

    Prefixed and part-qualified so it is unambiguous in a shared STL directory and never
    collides with a real union's `<union_id>.stl`. `zone_name` is author-supplied (a dict
    key from a part script's `result["keep_out"]`), so it is sanitized to a safe filename
    component before use -- otherwise a path separator or `..` segment could escape
    `stl_dir`.
    """
    return f"{KEEP_OUT_KEY}__{part_id}__{_sanitize_zone_name(zone_name)}.stl"


def keep_out_zone_key(part_id: str, zone_name: str) -> str:
    """Export-manifest / staleness key for a declared zone.

    `keep_out_check.py` can only ever recover the *sanitized* zone name (it discovers
    zones by parsing `keep_out_stl_name`'s filename, which is a lossy many-to-one map),
    so the writer (`write_assembly.py`) must key the manifest the same sanitized way, or a
    zone name containing any non-identifier character never matches between the two and
    staleness detection silently never fires for it.
    """
    return f"{part_id}::{_sanitize_zone_name(zone_name)}"


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
