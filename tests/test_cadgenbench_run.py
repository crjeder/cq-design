import itertools
import json
import sys
import zipfile
from pathlib import Path

import cadquery as cq
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "evals"))

import cadgenbench_run  # noqa: E402  # pyright: ignore[reportMissingImports]


def _extents(shape):
    bb = shape.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen), (bb.center.x, bb.center.y, bb.center.z)


def test_canonical_pose_orders_extents_and_centres():
    for dims in [(10, 30, 20), (5, 10, 40), (40, 5, 10)]:
        box = cq.Workplane().box(*dims).translate((7, -3, 11)).findSolid()
        posed = cadgenbench_run.canonical_pose(box)
        extents, center = _extents(posed)
        assert [round(e, 3) for e in extents] == sorted(dims, reverse=True)
        assert all(abs(c) < 1e-6 for c in center)


def test_canonical_matrix_is_a_rotation_for_every_axis_order():
    for extents in itertools.permutations((1.0, 2.0, 3.0)):
        m = np.array(cadgenbench_run.canonical_matrix((0, 0, 0), extents))[:3, :3]
        assert np.allclose(m @ m.T, np.eye(3))
        assert np.isclose(np.linalg.det(m), 1.0)


def test_package_keeps_every_fixture_folder_and_does_not_agree(tmp_path):
    run = tmp_path / "run"
    (run / "101").mkdir(parents=True)
    (run / "101" / "output.step").write_text("x")
    meta = {
        "submitter_name": "a",
        "submission_name": "b",
        "agent_url": None,
        "notes": None,
        "agree_to_publish": False,
    }
    zip_path = cadgenbench_run.package(run, ["101", "201"], meta)
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert {"meta.json", "101/", "101/output.step", "201/"} <= names
        assert json.loads(zf.read("meta.json"))["agree_to_publish"] is False
