"""Regression: a valid, watertight part with four zero-thickness fins (CadQuery, slow)."""

from pathlib import Path

import cadquery as cq

import mesh_io
import quality_gate

FIXTURE = Path(__file__).parent / "fixtures" / "rim_fillet_fins.py.txt"
PRISM_LEN = ".extrude(TREAD_RADIUS * (1 - f / RIB_DEPTH))"
# End the prism where the rib is two fillets deep, clear of the chamfered bottom edge.
PRISM_LEN_FIXED = ".extrude(TREAD_RADIUS * (1 - 2 * f / RIB_DEPTH))"


def _export(src: str, tmp_path: Path) -> str:
    ns: dict = {"__name__": "fixture"}
    exec(compile(src, str(FIXTURE), "exec"), ns)
    stl = tmp_path / "part.stl"
    cq.exporters.export(ns["result"], str(stl), tolerance=0.02, angularTolerance=0.1)
    return str(stl)


def test_unmated_prism_fillet_leaves_four_fins(tmp_path):
    stl = _export(FIXTURE.read_text(encoding="utf-8"), tmp_path)
    issues = quality_gate._analyze_stl(stl, 45.0)
    fins = [i for i in issues if i["type"] == "sliver_fin"]
    assert len(fins) == 1
    assert fins[0]["fold_count"] == 4
    assert fins[0]["sharpest_interior_deg"] < 2.0
    # The mesh is otherwise fine: this is the class no other check sees.
    assert not [i for i in issues if i["type"] == "non_watertight"]


def test_ending_the_prism_on_the_rib_flank_removes_the_fins(tmp_path):
    src = FIXTURE.read_text(encoding="utf-8")
    assert PRISM_LEN in src
    stl = _export(src.replace(PRISM_LEN, PRISM_LEN_FIXED), tmp_path)
    assert mesh_io.fold_metrics(mesh_io.load_mesh(stl))["count"] == 0
