"""Integration tests for cq_warehouse hardware catalog."""

import json
import os
import subprocess
import sys

import pytest

WRAPPER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src",
    "run_cadquery_model.py",
)
FIXTURE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "fixtures",
    "cq_warehouse_fastener.py",
)

pytest.importorskip("cq_warehouse", reason="cq_warehouse not installed")


def run(script_path, *extra_args):
    result = subprocess.run(
        [sys.executable, WRAPPER, str(script_path), *extra_args],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout) if result.stdout.strip() else {}
    return result.returncode, data


def test_cq_warehouse_script_succeeds(tmp_path):
    """A script using cq_warehouse fasteners runs cleanly through the wrapper."""
    import shutil

    script = tmp_path / "cq_warehouse_fastener.py"
    shutil.copy(FIXTURE, script)

    rc, data = run(script)
    assert rc == 0, f"wrapper failed: {data}"
    assert data["success"] is True
    assert data["errors"] == []


def test_cq_warehouse_geometry_reported(tmp_path):
    """Wrapper reports geometry for a cq_warehouse-based model."""
    import shutil

    script = tmp_path / "cq_warehouse_fastener.py"
    shutil.copy(FIXTURE, script)

    rc, data = run(script, "--strict")
    assert rc == 0
    assert data["geometry"] is not None
    assert data["geometry"]["bbox"]["x_mm"] > 0
    assert data["watertight"] is True


def test_fastener_part_dimensions():
    """cq_warehouse fastener objects carry correct dimensional attributes."""
    from cq_warehouse.fastener import HexHeadScrew, HexNut  # type: ignore[import-untyped]

    bolt = HexHeadScrew(size="M6-1", length=20, fastener_type="iso4014", simple=True)
    nut = HexNut(size="M6-1", fastener_type="iso4033", simple=True)

    # Parts are CadQuery Solids with bounding box
    import cadquery as cq

    bolt_bb = cq.Workplane().add(bolt).val().BoundingBox()
    assert bolt_bb.zmax - bolt_bb.zmin > 0

    nut_bb = cq.Workplane().add(nut).val().BoundingBox()
    assert nut_bb.zmax - nut_bb.zmin > 0
