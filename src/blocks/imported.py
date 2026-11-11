"""Checked STEP/BREP import.

``import_solid(path)`` imports a file and checks it against the grader's criterion:
``BRepCheck_Analyzer.IsValid()``, a solid, and ``mesh_gate.mesh_gate_error`` is None. A
passing import is returned untouched (healing a valid input can break it: CADGenBench
206, 215, 238). A failing one goes through a staged ShapeFix heal at
``heal_tol = max(0.1 mm, largest edge tolerance)``; each stage works on the previous
stage's in-memory output (reloading between stages breaks 217), and the check runs on
the stage's STEP round trip, because the grader only sees the reloaded file (in-memory
BRepCheck disagrees with it in both directions):

1. ``wire``: ShapeFix_Shape with the tail/notch/small-edge/self-intersection fixes on
2. ``small_edges``: ShapeFix_Wireframe drops/merges small edges
3. ``small_faces``: ShapeFix_FixSmallFace removes spot and strip faces

The first stage that passes within ``max_volume_deviation`` wins and its in-memory shape
is returned, not the reload: exporting the reload again is invalid for 217 and 240, while
exporting the in-memory shape yields exactly the file that was checked. Otherwise a
``[cq-verify:step_unrepairable:<name>]`` RuntimeError the wrapper maps to a typed error.
"""

import json
from pathlib import Path

import cadquery as cq
from OCP.BRep import BRep_Tool
from OCP.BRepCheck import BRepCheck_Analyzer, BRepCheck_NoError, BRepCheck_Status
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.ShapeFix import ShapeFix_FixSmallFace, ShapeFix_Shape, ShapeFix_Wireframe
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape

try:
    from mesh_gate import mesh_gate_error, step_roundtrip
except ImportError:  # lib/ bundles and standalone exports don't ship mesh_gate

    def mesh_gate_error(shape) -> str | None:
        return None

    def step_roundtrip(shape):
        return shape


HEAL_TOL_MIN_MM = 0.1
_SUB_SHAPES = (
    (TopAbs_SOLID, "Solid"),
    (TopAbs_SHELL, "Shell"),
    (TopAbs_FACE, "Face"),
    (TopAbs_EDGE, "Edge"),
    (TopAbs_VERTEX, "Vertex"),
)


def _subs(shape, kind) -> list:
    m = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, m)
    return [m.FindKey(i) for i in range(1, m.Size() + 1)]


def brep_statuses(shape) -> list[str]:
    """Return de-duplicated '<Solid|Shell|Face|...>: <BRepCheck status>' strings; [] = valid."""
    analyzer = BRepCheck_Analyzer(shape)
    if analyzer.IsValid():
        return []
    out: list[str] = []
    for kind, name in _SUB_SHAPES:
        for sub in _subs(shape, kind):
            res = analyzer.Result(sub)
            if res is None:
                continue
            for st in res.Status():
                msg = f"{name}: {BRepCheck_Status(st).name}"
                if st != BRepCheck_NoError and msg not in out:
                    out.append(msg)
    return out or ["Shape: BRepCheck invalid"]


def _volume(shape) -> float:
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return abs(props.Mass())


def _problems(shape) -> list[str]:
    """The grader's criterion: BRepCheck statuses, a solid, then the mesh gate; [] = passes."""
    found = brep_statuses(shape)
    if not _subs(shape, TopAbs_SOLID):
        found.append("no solid (shell only)")
    if not found:
        reason = mesh_gate_error(shape)
        if reason:
            found.append(f"mesh gate: {reason}")
    return found


def _reload(shape):
    """`shape` after a STEP round trip: one solid if there is exactly one, else the compound."""
    wrapped = step_roundtrip(shape)
    solids = _subs(wrapped, TopAbs_SOLID)
    return solids[0] if len(solids) == 1 else wrapped


def _max_edge_tol(shape) -> float:
    return max(
        (BRep_Tool.Tolerance_s(TopoDS.Edge_s(e)) for e in _subs(shape, TopAbs_EDGE)), default=0.0
    )


def _wire(shape, tol):
    fix = ShapeFix_Shape(shape)
    fix.SetPrecision(1e-7)
    fix.SetMaxTolerance(tol)
    wire = fix.FixWireTool()
    wire.FixTailMode = 1
    wire.FixNotchedEdgesMode = 1
    wire.FixSmallMode = 1
    wire.FixSelfIntersectionMode = 1
    wire.FixNonAdjacentIntersectingEdgesMode = 1
    wire.SetMaxTailWidth(tol)
    wire.SetMaxTailAngle(0.1)
    fix.Perform()
    return fix.Shape()


def _small_edges(shape, tol):
    fix = ShapeFix_Wireframe(shape)
    fix.SetPrecision(tol)
    fix.ModeDropSmallEdges = 1
    fix.FixSmallEdges()
    fix.FixWireGaps()
    return fix.Shape()


def _small_faces(shape, tol):
    fix = ShapeFix_FixSmallFace()
    fix.Init(shape)
    fix.SetPrecision(tol)
    fix.SetMaxTolerance(tol)
    fix.Perform()
    return fix.FixShape()


_STAGES = (("wire", _wire), ("small_edges", _small_edges), ("small_faces", _small_faces))


def import_solid(path, max_volume_deviation: float = 0.01) -> cq.Workplane:
    """Import a .step/.stp/.brep solid, healing it only when it fails the grader's check."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext in (".step", ".stp"):
        shape = cq.importers.importStep(str(path)).findSolid().wrapped
    elif ext == ".brep":
        shape = cq.Shape.importBrep(str(path)).wrapped
    else:
        raise ValueError(f"import_solid accepts .step, .stp or .brep, not {path.name}")
    problems = _problems(shape)
    if not problems:
        return cq.Workplane("XY").add(cq.Shape.cast(shape))

    # ponytail: healed solid is not cached, so a broken file is re-healed on every run
    # (tens of seconds on ~2k faces); cache by file hash if that cost shows up.
    v0 = _volume(shape)
    tol = max(HEAL_TOL_MIN_MM, _max_edge_tol(shape))
    strategy: list[str] = []
    delta = 0.0
    for name, stage in _STAGES:
        try:
            shape = stage(shape, tol)
            reloaded = _reload(shape)
        except Exception as exc:  # an OCC failure ends the heal
            problems = [f"stage {name} raised {type(exc).__name__}: {exc}"]
            break
        strategy.append(name)
        delta = (_volume(reloaded) - v0) / v0 if v0 else 0.0
        if abs(delta) > max_volume_deviation:
            problems = [f"volume changed {delta:+.2%} > {max_volume_deviation:.2%} after {name}"]
            break
        problems = _problems(reloaded)
        if not problems:
            info = {
                "file": path.name,
                "strategy": strategy,
                "heal_tol_mm": round(tol, 4),
                "volume_delta_pct": round(delta * 100, 4),
            }
            print("[cq-design:step-repair] " + json.dumps(info))
            return cq.Workplane("XY").add(cq.Shape.cast(shape))
    raise RuntimeError(
        f"[cq-verify:step_unrepairable:{path.name}] {'; '.join(problems)} "
        f"(stages tried: {', '.join(strategy) or 'none'}, volume delta {delta:+.4%})"
    )
