#!/usr/bin/env python3
"""Probes: measurable intent checks evaluated on a BRep body, no meshing.

Kinds (all points in the frame of the body they are checked against):

- ``solid_at(p)`` -- point inside material.
- ``empty_at(p)`` -- point outside material.
- ``ray(p, dir, hits, length=None)`` -- face crossings along the line through ``p``
  (a segment of ``length`` centered on ``p`` when given): 0 for an open bore.
- ``bbox(lo, hi, tol)`` / ``bbox(size=..., mode=...)`` -- body extents. ``mode="within"``
  only bounds the size (a part's envelope while it is still being built).
- ``delta(sign)`` -- volume change of a ``place`` step (checked by the step itself).

A ``Registry`` accumulates probes with an owner (``"plan"`` or a step index) and
re-checks all of them after every step. A block-owned point probe that lies inside a
later step's tool is retired by that step; plan-owned probes never retire.

Usage:
    python3 probes.py plan BUILD_PLAN.json --part <id>
"""

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, field, replace
from typing import Any

# Interface type -> probe family. Not builder judgment: the plan's type picks the probes.
CUT_TYPES = frozenset(
    {
        "clearance_opening",
        "port_cutout",
        "cable_slot",
        "vent_grid",
        "bore",
        "hole",
        "pocket",
        "cutout",
        "slot",
        "screw_mount",
        "screw_hole",
        "nut_trap",
    }
)
# Cut types whose opening runs through the wall, so a ray along the wall axis is open.
THROUGH_TYPES = frozenset({"clearance_opening", "port_cutout", "cable_slot", "bore", "hole"})
BOSS_TYPES = frozenset({"union", "boss", "screw_boss", "pcb_standoff", "pin", "post"})
WALL_AXIS = {
    "top": (0, 0, 1),
    "bottom": (0, 0, 1),
    "north": (0, 1, 0),
    "south": (0, 1, 0),
    "front": (0, 1, 0),
    "back": (0, 1, 0),
    "east": (1, 0, 0),
    "west": (1, 0, 0),
    "left": (1, 0, 0),
    "right": (1, 0, 0),
}
ENVELOPE_TOL_MM = 0.5
# Probe points stay at least this far from the entry's own faces (OCC classifier noise).
MIN_FACE_DIST_MM = 0.1


@dataclass
class Probe:
    kind: str
    p: tuple[float, float, float] | None = None
    dir: tuple[float, float, float] | None = None
    hits: int | None = None
    length: float | None = None
    lo: tuple[float, float, float] | None = None
    hi: tuple[float, float, float] | None = None
    size: tuple[float, float, float] | None = None
    tol: float = 0.1
    mode: str = "exact"
    sign: int | None = None
    owner: str | int = "plan"
    label: str = ""

    def key(self) -> tuple:
        """Identity for failure history: (owner, kind, rounded location)."""
        loc = tuple(round(v, 1) for v in self.p) if self.p else None
        return (self.owner, self.kind, loc)


def solid_at(p, label: str = "") -> Probe:
    return Probe("solid_at", p=tuple(p), label=label)


def empty_at(p, label: str = "") -> Probe:
    return Probe("empty_at", p=tuple(p), label=label)


def ray(p, dir, hits: int, length: float | None = None, label: str = "") -> Probe:
    return Probe("ray", p=tuple(p), dir=tuple(dir), hits=hits, length=length, label=label)


def bbox(lo=None, hi=None, tol: float = 0.1, size=None, mode: str = "exact", label="") -> Probe:
    return Probe(
        "bbox",
        lo=tuple(lo) if lo else None,
        hi=tuple(hi) if hi else None,
        size=tuple(size) if size else None,
        tol=tol,
        mode=mode,
        label=label,
    )


def delta(sign: int, label: str = "") -> Probe:
    return Probe("delta", sign=sign, label=label)


def _wrapped(shape):
    return shape.wrapped if hasattr(shape, "wrapped") else shape


def _solids(shape) -> list:
    return shape.Solids() if hasattr(shape, "Solids") else [shape]


def classify(shape, p) -> str:
    """'IN', 'OUT' or 'ON' for point p against a solid or a compound of solids."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN, TopAbs_OUT

    states = {
        BRepClass3d_SolidClassifier(_wrapped(s), gp_Pnt(*p), 1e-6).State() for s in _solids(shape)
    }
    return "IN" if TopAbs_IN in states else "OUT" if states <= {TopAbs_OUT} else "ON"


def ray_hits(shape, p, d, length: float | None = None) -> int:
    """Number of face crossings along the line (or centered segment) through p."""
    from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector

    half = length / 2 if length else 1e6
    total = 0
    for s in _solids(shape):
        it = IntCurvesFace_ShapeIntersector()
        it.Load(_wrapped(s), 1e-6)
        it.Perform(gp_Lin(gp_Pnt(*p), gp_Dir(*d)), -half, half)
        total += it.NbPnt()
    return total


def face_distance(shape, p) -> float:
    """Distance from p to the nearest face of shape (inside or outside)."""
    import cadquery as cq

    faces = cq.Compound.makeCompound(shape.Faces())
    return cq.Vertex.makeVertex(*p).distance(faces)


def _extents(shape):
    bb = shape.BoundingBox()
    return (bb.xmin, bb.ymin, bb.zmin), (bb.xmax, bb.ymax, bb.zmax)


def evaluate(probe: Probe, shape) -> tuple[bool, Any]:
    """Check one probe on shape. Returns (ok, observed value)."""
    k = probe.kind
    if k in ("solid_at", "empty_at"):
        got = classify(shape, probe.p)
        return got == ("IN" if k == "solid_at" else "OUT"), got
    if k == "ray":
        got = ray_hits(shape, probe.p, probe.dir, probe.length)
        return got == probe.hits, got
    if k == "bbox":
        lo, hi = _extents(shape)
        size = tuple(b - a for a, b in zip(lo, hi, strict=True))
        got = {"lo": [round(v, 3) for v in lo], "hi": [round(v, 3) for v in hi]}
        if probe.size is not None:
            if probe.mode == "within":
                ok = all(s <= e + probe.tol for s, e in zip(size, probe.size, strict=True))
            else:
                ok = all(abs(s - e) <= probe.tol for s, e in zip(size, probe.size, strict=True))
            return ok, got
        ok = all(abs(a - b) <= probe.tol for a, b in zip(lo, probe.lo, strict=True)) and all(
            abs(a - b) <= probe.tol for a, b in zip(hi, probe.hi, strict=True)
        )
        return ok, got
    raise ValueError(f"probe kind {k!r} is checked by its step, not evaluated on a body")


def _rotate(v, rot) -> tuple[float, float, float]:
    """Rotate v by successive X, Y, Z angles in degrees (CadQuery Location convention)."""
    x, y, z = v
    ax, ay, az = (math.radians(a) for a in rot)
    y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
    x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
    x, y = x * math.cos(az) - y * math.sin(az), x * math.sin(az) + y * math.cos(az)
    return (x, y, z)


def transform(probe: Probe, at=(0, 0, 0), rotate=(0, 0, 0)) -> Probe:
    """Return probe moved from an entry's local frame by rotate (deg XYZ) then at."""

    def move(p):
        r = _rotate(p, rotate)
        return tuple(a + b for a, b in zip(r, at, strict=True))

    return replace(
        probe,
        p=move(probe.p) if probe.p else None,
        dir=_rotate(probe.dir, rotate) if probe.dir else None,
    )


@dataclass
class Registry:
    probes: list[Probe] = field(default_factory=list)
    retired: list[Probe] = field(default_factory=list)

    def add(self, probes, owner) -> None:
        self.probes.extend(replace(p, owner=owner) for p in probes)

    def retire_inside(self, tool, step: int) -> list[Probe]:
        """Retire block-owned point probes lying inside tool (a placed step's solid)."""
        keep, gone = [], []
        for p in self.probes:
            if p.owner != "plan" and p.p is not None and classify(tool, p.p) != "OUT":
                gone.append(p)
            else:
                keep.append(p)
        self.probes = keep
        self.retired.extend(gone)
        return gone

    def check(self, shape, final: bool = False) -> tuple[int, list[dict]]:
        """Check every live probe. bbox probes in 'within' mode become exact when final."""
        failed = []
        for p in self.probes:
            probe = replace(p, mode="exact") if final and p.kind == "bbox" else p
            ok, got = evaluate(probe, shape)
            if not ok:
                failed.append({**as_dict(p), "got": got})
        return len(self.probes), failed


def as_dict(p: Probe) -> dict:
    return {k: v for k, v in asdict(p).items() if v is not None}


def plan_probes(part: dict) -> tuple[list[Probe], list[str]]:
    """Seed step-0 probes from a plan part entry. Returns (probes, unprobed interface names).

    The ``solids == 1`` invariant is not a probe: the step loop checks it after every
    step from the first ``place``.
    """
    probes: list[Probe] = []
    unprobed: list[str] = []
    dims = part.get("dimensions") or {}
    if {"w_mm", "d_mm", "h_mm"} <= dims.keys():
        size = (dims["w_mm"], dims["d_mm"], dims["h_mm"])
        probes.append(bbox(size=size, tol=ENVELOPE_TOL_MM, mode="within", label="envelope"))
    for i, itf in enumerate(part.get("interfaces", [])):
        name = itf.get("name") or f"interfaces[{i}]"
        pos, t = itf.get("position_mm"), itf.get("type")
        width = itf.get("diameter_mm") or min(itf.get("size_mm") or [0]) or None
        if pos is None or width is None or t not in CUT_TYPES | BOSS_TYPES:
            unprobed.append(name)
            continue
        if t in BOSS_TYPES:
            probes.append(solid_at(pos, label=name))
            continue
        probes.append(empty_at(pos, label=name))
        axis = WALL_AXIS.get(str(itf.get("wall", "")).lower())
        if t in THROUGH_TYPES and axis:
            probes.append(ray(pos, axis, hits=0, length=2 * width, label=name))
    return probes, unprobed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("plan", help="print the step-0 probes a plan part entry seeds")
    pp.add_argument("plan")
    pp.add_argument("--part", required=True)
    args = ap.parse_args(argv)

    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)
    part = next((p for p in plan.get("parts", []) if p.get("id") == args.part), None)
    if part is None:
        print(json.dumps({"error": f"no part {args.part!r} in plan"}))
        return 1
    probes, unprobed = plan_probes(part)
    print(
        json.dumps(
            {
                "part_id": args.part,
                "probes": [as_dict(p) for p in probes],
                "unprobed_interfaces": unprobed,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
