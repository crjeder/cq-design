"""Checked STEP/BREP import.

``import_solid(path)`` imports a file and checks it: ``BRepCheck_Analyzer.IsValid()``
plus no face below ``SLIVER_AREA_MM2`` (a zero-area face is BRep-valid but folds into
a non-manifold mesh). An invalid import is repaired topologically, cheapest rung first,
each rung working on the previous one's output:

1. remove sliver faces, sew, rebuild the solid
2. defeature the faces BRepCheck flags
3. replace each flagged face with a filling patch over its outer wire, sew

A repair must also pass ``mesh_gate.mesh_gate_error`` (the grader's mesh stage); a valid
import skips that check. Tolerance-only fixes are deliberately absent: STEP export drops
per-edge tolerances, so such a "repair" is invalid again on reload. A repair whose volume
differs from the import by more than ``max_volume_deviation`` is rejected; an unrepairable
file raises a
``[cq-verify:step_unrepairable:<name>]`` RuntimeError the wrapper maps to a typed error.
"""

import json
from pathlib import Path

import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Defeaturing
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
from OCP.BRepCheck import BRepCheck_Analyzer, BRepCheck_NoError, BRepCheck_Status
from OCP.BRepGProp import BRepGProp
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeFilling
from OCP.BRepTools import BRepTools_ReShape
from OCP.GeomAbs import GeomAbs_C0
from OCP.GProp import GProp_GProps
from OCP.ShapeFix import ShapeFix_Shape, ShapeFix_Solid
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape

try:
    from mesh_gate import mesh_gate_error
except ImportError:  # lib/ bundles and standalone exports don't ship mesh_gate

    def mesh_gate_error(shape) -> str | None:
        return None


SLIVER_AREA_MM2 = 1e-3
SEW_TOL_MM = 1e-2  # 1e-3 left CADGenBench 250's shell open after sliver removal
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


def _area(face) -> float:
    props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, props)
    return props.Mass()


def _volume(shape) -> float:
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return abs(props.Mass())


def _slivers(shape) -> list:
    return [TopoDS.Face_s(f) for f in _subs(shape, TopAbs_FACE) if _area(f) < SLIVER_AREA_MM2]


def _flagged(shape) -> list:
    analyzer = BRepCheck_Analyzer(shape)
    out = []
    for f in _subs(shape, TopAbs_FACE):
        res = analyzer.Result(f)
        if res is not None and any(st != BRepCheck_NoError for st in res.Status()):
            out.append(TopoDS.Face_s(f))
    return out


def _problems(shape) -> list[str]:
    """Cheap validity check: BRepCheck statuses plus a sliver-face count."""
    found = brep_statuses(shape)
    if not _subs(shape, TopAbs_SOLID):
        found.append("no solid (shell only)")
    n = len(_slivers(shape))
    return found + ([f"{n} face(s) below {SLIVER_AREA_MM2} mm2"] if n else [])


def _solid_from_shells(shape):
    make = BRepBuilderAPI_MakeSolid()
    for shell in _subs(shape, TopAbs_SHELL):
        make.Add(TopoDS.Shell_s(shell))
    fix = ShapeFix_Solid(make.Solid())
    fix.Perform()
    return fix.Solid()


def _sew_solid(shapes: list):
    sew = BRepBuilderAPI_Sewing(SEW_TOL_MM)
    for s in shapes:
        sew.Add(s)
    sew.Perform()
    # ShapeFix_Shape clears edge/vertex bookkeeping BRepCheck rejects after sewing (moves no
    # geometry) but can demote the solid to a bare shell, so the solid is rebuilt after it.
    final = ShapeFix_Shape(_solid_from_shells(sew.SewedShape()))
    final.Perform()
    shape = final.Shape()
    return shape if _subs(shape, TopAbs_SOLID) else _solid_from_shells(shape)


def _drop_slivers(shape):
    faces = _slivers(shape)
    if not faces:
        return shape, 0
    reshape = BRepTools_ReShape()
    for f in faces:
        reshape.Remove(f)
    return _sew_solid([reshape.Apply(shape)]), len(faces)


def _defeature(shape):
    faces = _flagged(shape)
    if not faces:
        return shape, 0
    algo = BRepAlgoAPI_Defeaturing()
    algo.SetShape(shape)
    for f in faces:
        algo.AddFaceToRemove(f)
    algo.Build()
    removed = sum(algo.IsDeleted(f) for f in faces) if algo.IsDone() else 0
    # IsDone() with nothing deleted is a no-op (CADGenBench 202); don't report it as a rung
    return (algo.Shape(), removed) if removed else (shape, 0)


def _patch(shape):
    faces = _flagged(shape)
    if not faces:
        return shape, 0
    reshape = BRepTools_ReShape()
    patches = []
    for f in faces:
        reshape.Remove(f)
        fill = BRepOffsetAPI_MakeFilling()
        for e in cq.Face(f).outerWire().Edges():
            fill.Add(e.wrapped, GeomAbs_C0)
        fill.Build()
        patches.append(fill.Shape())
    return _sew_solid([reshape.Apply(shape), *patches]), len(faces)


_LADDER = (("drop_slivers", _drop_slivers), ("defeature", _defeature), ("patch", _patch))


def import_solid(path, max_volume_deviation: float = 0.01) -> cq.Workplane:
    """Import a .step/.stp/.brep solid, repairing it topologically when invalid."""
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

    # ponytail: repaired solid is not cached, so a broken file is re-repaired on every
    # run (seconds on ~2k faces); cache by file hash if that cost shows up.
    v0 = _volume(shape)
    strategy: list[str] = []
    removed = 0
    delta = 0.0
    for name, rung in _LADDER:
        try:
            repaired, n = rung(shape)
        except Exception:  # an OCC failure on one rung leaves the next rung to try
            continue
        if not n:
            continue
        shape, removed = repaired, removed + n
        strategy.append(name)
        delta = (_volume(shape) - v0) / v0 if v0 else 0.0
        if abs(delta) > max_volume_deviation:
            problems = [f"volume changed {delta:+.2%} > {max_volume_deviation:.2%} after {name}"]
            break
        problems = _problems(shape)
        if not problems:
            # a BRep-valid repair can still fail the grader mesh gate (CADGenBench 202's
            # filling patch); every edit of it would then be blocked as invalid_mesh
            reason = mesh_gate_error(shape)
            if reason:
                problems = [f"repair fails the mesh gate: {reason}"]
                continue
            info = {
                "file": path.name,
                "strategy": strategy,
                "faces_removed": removed,
                "volume_delta_pct": round(delta * 100, 4),
            }
            print("[cq-design:step-repair] " + json.dumps(info))
            return cq.Workplane("XY").add(cq.Shape.cast(shape))
    raise RuntimeError(
        f"[cq-verify:step_unrepairable:{path.name}] {'; '.join(problems)} "
        f"(rungs tried: {', '.join(strategy) or 'none applicable'}, volume delta {delta:+.4%})"
    )
