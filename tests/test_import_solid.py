"""blocks.import_solid (checked STEP/BREP import) and the wrapper's per-run BRepCheck."""

import json
from pathlib import Path

import cadquery as cq
import pytest
from conftest import run_wrapper as run
from OCP.BRepTools import BRepTools_ReShape

from blocks import import_solid


def _slab_brep(tmp_path):
    """Two blocks glued through a 5e-5 mm slab: its 4 outer faces are below the sliver limit."""
    half = cq.Workplane().box(10, 5, 10, centered=(True, False, True))
    slab = cq.Workplane().box(10, 5e-5, 10, centered=(True, False, True))
    body = (
        half.translate((0, -5, 0))
        .union(slab, clean=False)
        .union(half.translate((0, 5e-5, 0)), clean=False)
    )
    path = tmp_path / "slab.brep"
    body.findSolid().exportBrep(str(path))
    return path


def _open_box_brep(tmp_path):
    """A box missing one face: BRep-invalid and beyond every repair rung."""
    box = cq.Workplane().box(10, 10, 10).findSolid()
    reshape = BRepTools_ReShape()
    reshape.Remove(box.Faces()[0].wrapped)
    path = tmp_path / "open.brep"
    cq.Shape.cast(reshape.Apply(box.wrapped)).exportBrep(str(path))
    return path


def test_valid_step_unchanged(tmp_path, capsys):
    step = tmp_path / "box.step"
    cq.exporters.export(cq.Workplane().box(20, 10, 5), str(step))
    shape = import_solid(step).findSolid()
    assert shape.isValid() and len(shape.Faces()) == 6
    assert abs(shape.Volume() - 1000) < 1e-6
    assert capsys.readouterr().out == ""


def test_other_extension_rejected(tmp_path):
    with pytest.raises(ValueError, match=r"\.step"):
        import_solid(tmp_path / "part.stl")


def _fail_first_gate(monkeypatch):
    """Make the gate reject the raw import once, so the heal runs on an otherwise valid body."""
    import blocks.imported

    calls = []

    def gate(shape):
        calls.append(1)
        return "mesh not closed: 3 open edges" if len(calls) == 1 else None

    monkeypatch.setattr(blocks.imported, "mesh_gate_error", gate)


def test_sliver_face_passing_gate_is_untouched(tmp_path, capsys):
    path = _slab_brep(tmp_path)
    raw = cq.Shape.importBrep(str(path))
    shape = import_solid(path).findSolid()
    assert len(shape.Faces()) == len(raw.Faces())
    assert capsys.readouterr().out == ""


def test_heal_reported(tmp_path, capsys, monkeypatch):
    _fail_first_gate(monkeypatch)
    assert import_solid(_slab_brep(tmp_path)).findSolid().isValid()
    line = capsys.readouterr().out.strip()
    assert line.startswith("[cq-design:step-repair] ")
    info = json.loads(line.split(" ", 1)[1])
    assert info["strategy"] == ["wire"] and info["heal_tol_mm"] >= 0.1
    assert abs(info["volume_delta_pct"]) < 0.01 and "faces_removed" not in info


def test_heal_failing_mesh_gate_is_unrepairable(tmp_path, monkeypatch):
    import blocks.imported

    monkeypatch.setattr(
        blocks.imported, "mesh_gate_error", lambda s: "mesh not closed: 3 open edges"
    )
    with pytest.raises(RuntimeError, match=r"step_unrepairable:slab\.brep\] mesh gate: mesh not"):
        import_solid(_slab_brep(tmp_path))


def test_volume_limit_rejects_heal(tmp_path, monkeypatch):
    import blocks.imported

    _fail_first_gate(monkeypatch)
    grow = lambda s, tol: cq.Shape.cast(s).scale(1.02).wrapped  # noqa: E731
    monkeypatch.setattr(blocks.imported, "_STAGES", (("wire", grow),))
    with pytest.raises(RuntimeError, match=r"\[cq-verify:step_unrepairable:slab\.brep\] volume"):
        import_solid(_slab_brep(tmp_path))


def test_unrepairable_raises_marker(tmp_path):
    with pytest.raises(RuntimeError, match=r"\[cq-verify:step_unrepairable:open\.brep\]"):
        import_solid(_open_box_brep(tmp_path))


def test_wrapper_maps_unrepairable(tmp_path):
    path = _open_box_brep(tmp_path)
    script = tmp_path / "imp.py"
    script.write_text(f"from blocks import import_solid\nresult = import_solid(r'{path}')\n")
    rc, data = run(script)
    assert rc == 1 and data["success"] is False
    assert [e["type"] for e in data["errors"]] == ["step_unrepairable"]


def test_wrapper_no_brep_error_when_valid(good_script):
    rc, data = run(good_script)
    assert rc == 0
    assert not [e for e in data["errors"] if e["type"] == "invalid_brep"]


_OPEN_BOX = (
    "import cadquery as cq\n"
    "from OCP.BRepTools import BRepTools_ReShape\n"
    "def open_box():\n"
    "    box = cq.Workplane().box(10, 10, 10).val()\n"
    "    rs = BRepTools_ReShape()\n"
    "    rs.Remove(box.Faces()[0].wrapped)\n"
    "    return cq.Workplane().add(cq.Shape.cast(rs.Apply(box.wrapped)))\n"
)


def test_wrapper_blocks_invalid_result(tmp_path):
    script = tmp_path / "bad.py"
    script.write_text(_OPEN_BOX + "result = open_box()\n")
    rc, data = run(script)
    assert rc == 1 and data["success"] is False
    errs = [e for e in data["errors"] if e["type"] == "invalid_brep"]
    assert len(errs) == 1 and "BRepCheck" in errs[0]["message"]


_TETRA = [(0, 2, 1), (0, 1, 3), (1, 2, 3), (0, 3, 2)]


@pytest.mark.parametrize(
    "tris, match",
    [
        (_TETRA[:3], "not closed: 3 open"),
        (_TETRA + [(0, 1, 4), (0, 4, 1)], "shared by 4"),
        ([(0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 3, 2)], "orientation"),
    ],
)
def test_mesh_validate_rejects(tris, match):
    import numpy as np

    from mesh_gate import MeshGateError, _validate

    with pytest.raises(MeshGateError, match=match):
        _validate(np.array(tris))


def test_mesh_gate_passes_closed_solids():
    import numpy as np

    from mesh_gate import _validate, mesh_gate_error

    _validate(np.array(_TETRA))
    body = cq.Workplane().box(20, 10, 5).faces(">Z").workplane().hole(4).edges("|Z").fillet(1)
    assert mesh_gate_error(body.findSolid().wrapped) is None


def test_mesh_gate_rejects_endpoint_mismatch(monkeypatch):
    import OCP.BRep
    from OCP.gp import gp_Pnt

    from mesh_gate import mesh_gate_error

    real = OCP.BRep.BRep_Tool

    class Shifted:
        Triangulation_s = staticmethod(real.Triangulation_s)

        @staticmethod
        def Pnt_s(v):  # noqa: N802
            p = real.Pnt_s(v)
            return gp_Pnt(p.X() + 1.0, p.Y(), p.Z())

    monkeypatch.setattr(OCP.BRep, "BRep_Tool", Shifted)
    body = cq.Workplane().box(20, 10, 5).findSolid()
    reason = mesh_gate_error(body.wrapped)
    assert reason and "inconsistent with FirstVertex/LastVertex" in reason


def test_mesh_sidecar_maps_to_invalid_mesh(tmp_path):
    from run_cadquery_model import _brep_errors

    (tmp_path / "brep_check.json").write_text(
        json.dumps({"a": ["Mesh: mesh not closed: 12 open edges"], "b": []})
    )
    errs = _brep_errors(str(tmp_path))
    assert [(e["type"], e["union"]) for e in errs] == [("invalid_mesh", "a")]
    assert "12 open edges" in errs[0]["message"]


def test_wrapper_attributes_invalid_union(tmp_path):
    script = tmp_path / "multi.py"
    script.write_text(
        _OPEN_BOX
        + "base = cq.Workplane().box(5, 5, 5).translate((20, 0, 0))\n"
        + "result = {'base': base, 'lid': open_box()}\n"
    )
    rc, data = run(script)
    errs = [e for e in data["errors"] if e["type"] == "invalid_brep"]
    assert rc == 1 and [e["union"] for e in errs] == ["lid"]


_CGB = Path(__file__).resolve().parent.parent / "evals" / "runs" / "cadgenbench-data"


@pytest.mark.slow
@pytest.mark.skipif(not _CGB.is_dir(), reason="cadgenbench-data not present")
@pytest.mark.parametrize("fid", ["202", "217", "240", "250"])
def test_cadgenbench_invalid_input_heals(fid, capsys):
    step = _CGB / fid / "input.step"
    raw = cq.importers.importStep(str(step)).findSolid()
    healed = import_solid(step).findSolid()
    assert abs(healed.Volume() - raw.Volume()) / raw.Volume() < 5e-4
    assert "[cq-design:step-repair]" in capsys.readouterr().out


@pytest.mark.slow
@pytest.mark.skipif(not _CGB.is_dir(), reason="cadgenbench-data not present")
def test_cadgenbench_valid_input_unchanged(capsys):
    import_solid(_CGB / "206" / "input.step")
    assert capsys.readouterr().out == ""
