# mypy: ignore-errors
# type: ignore  # CAD stub-union noise; tests are ruff-linted, not type-checked
"""Gridfinity blocks and conformance check.

The assertions here are the published standard, not this implementation's opinions: grid
pitch, height unit, foot profile, stacking clearance. If one of them starts failing, the
parts stopped fitting the ecosystem -- that is the whole point of the module.
"""

import json
import os
import subprocess
import sys

import cadquery as cq
import pytest
from conftest import run_wrapper as run

from blocks.gridfinity import (
    BASE_PROFILE_HEIGHT_MM,
    GRID_CLEARANCE_MM,
    GRID_PITCH_MM,
    HEIGHT_UNIT_MM,
    LIP_FILLET_MM,
    STACKING_LIP_HEIGHT_MM,
    gridfinity_baseplate,
    gridfinity_bin,
    gridfinity_dimensions,
    gridfinity_feet,
    gridfinity_socket_cutter,
    gridfinity_units_for,
    lip_height,
)
from gridfinity_check import run_gridfinity_check

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "src")
# Contact between mating faces registers as a sliver of intersection volume; anything
# real is orders of magnitude larger.
CONTACT_TOL_MM3 = 5.0
# A bin seats 0.35 mm into a lip/socket (the profile clearance); probe just clear of it.
SEAT_MM = 0.35 - 0.05


def _bbox(workplane):
    return workplane.val().BoundingBox()


def _overlap(a, b, dz=0.0):
    """Intersection volume of two solids with `b` raised by `dz`."""
    moved = b.val().moved(cq.Location(cq.Vector(0, 0, dz)))
    result = a.val().intersect(moved)
    return result.Volume() if result is not None else 0.0


def _write(tmp_path, name, body):
    script = tmp_path / name
    script.write_text(body)
    return script


# --- geometry against the standard --------------------------------------------------


def test_feet_match_the_base_profile():
    bb = _bbox(gridfinity_feet(1, 1))
    assert bb.xlen == pytest.approx(GRID_PITCH_MM - GRID_CLEARANCE_MM, abs=0.01)
    assert bb.ylen == pytest.approx(GRID_PITCH_MM - GRID_CLEARANCE_MM, abs=0.01)
    assert bb.zlen == pytest.approx(BASE_PROFILE_HEIGHT_MM, abs=0.01)
    assert bb.zmin == pytest.approx(0.0, abs=0.01)


def test_feet_are_one_pad_per_cell_on_the_grid():
    feet = gridfinity_feet(3, 2)
    slab = (
        cq.Workplane("XY")
        .box(400, 400, 0.02, centered=(True, True, False))
        .translate((0, 0, 0.05))
        .val()
    )
    pads = feet.val().intersect(slab).Solids()
    assert len(pads) == 6
    centers = sorted({round(p.Center().x, 2) for p in pads})
    assert centers == pytest.approx([-42.0, 0.0, 42.0], abs=0.01)


def test_magnet_and_screw_holes_remove_material():
    plain = gridfinity_feet(1, 1).val().Volume()
    drilled = gridfinity_feet(1, 1, magnet_holes=True, screw_holes=True).val().Volume()
    assert drilled < plain


@pytest.mark.parametrize(("cols", "rows", "height_u"), [(1, 1, 3), (2, 1, 2), (3, 2, 6)])
def test_bin_outer_dimensions(cols, rows, height_u):
    bb = _bbox(gridfinity_bin(cols, rows, height_u))
    assert bb.xlen == pytest.approx(cols * GRID_PITCH_MM - GRID_CLEARANCE_MM, abs=0.01)
    assert bb.ylen == pytest.approx(rows * GRID_PITCH_MM - GRID_CLEARANCE_MM, abs=0.01)
    # The rim is rounded by default, which blunts the lip's apex by sqrt(2) x the fillet.
    assert bb.zlen == pytest.approx(height_u * HEIGHT_UNIT_MM + lip_height(), abs=0.01)
    assert bb.zmin == pytest.approx(0.0, abs=0.01)


def test_sharp_lip_reaches_the_drawn_apex():
    bb = _bbox(gridfinity_bin(1, 1, 3, lip_fillet=0.0))
    assert bb.zlen == pytest.approx(3 * HEIGHT_UNIT_MM + STACKING_LIP_HEIGHT_MM, abs=0.01)
    assert lip_height(LIP_FILLET_MM) < STACKING_LIP_HEIGHT_MM


def test_bin_without_lip_is_a_whole_number_of_height_units():
    bb = _bbox(gridfinity_bin(1, 1, 3, stacking_lip=False))
    assert bb.zlen == pytest.approx(3 * HEIGHT_UNIT_MM, abs=0.01)


def test_solid_bin_is_a_blank():
    hollow = gridfinity_bin(1, 1, 3).val().Volume()
    blank = gridfinity_bin(1, 1, 3, solid=True).val().Volume()
    assert blank > hollow * 2


def test_dividers_and_features_add_material():
    plain = gridfinity_bin(2, 1, 3).val().Volume()
    for kwargs in ({"divisions_x": 3}, {"label_tab": True}, {"scoop": True}):
        assert gridfinity_bin(2, 1, 3, **kwargs).val().Volume() > plain


def test_baseplate_spans_the_full_pitch_and_tiles():
    bb = _bbox(gridfinity_baseplate(3, 2))
    assert bb.xlen == pytest.approx(3 * GRID_PITCH_MM, abs=0.01)
    assert bb.ylen == pytest.approx(2 * GRID_PITCH_MM, abs=0.01)
    assert bb.zlen == pytest.approx(BASE_PROFILE_HEIGHT_MM, abs=0.01)


def test_socket_cutter_opens_at_the_plate_top():
    bb = _bbox(gridfinity_socket_cutter(1, 1, plate_h=8.0))
    assert bb.zmax == pytest.approx(8.0, abs=0.01)
    assert bb.zlen == pytest.approx(BASE_PROFILE_HEIGHT_MM, abs=0.02)


@pytest.mark.parametrize(
    ("call", "kwargs"),
    [
        (gridfinity_bin, {"cols": 0}),
        (gridfinity_bin, {"height_u": 1}),  # no room for a cavity above the 7 mm base
        (gridfinity_baseplate, {"plate_h": 3.0}),
        (gridfinity_baseplate, {"magnet_holes": True}),  # default plate has no stock
    ],
)
def test_impossible_parameters_raise(call, kwargs):
    with pytest.raises(ValueError):
        call(**kwargs)


# --- the parts actually go together --------------------------------------------------


def test_bin_drops_into_a_baseplate():
    plate = gridfinity_baseplate(2, 1, plate_h=7.15)
    bin_ = gridfinity_bin(2, 1, 3)
    seated = 7.15 - BASE_PROFILE_HEIGHT_MM + SEAT_MM
    assert _overlap(plate, bin_, seated) < CONTACT_TOL_MM3


def test_bin_drops_into_each_cell_of_a_larger_plate():
    plate = gridfinity_baseplate(2, 2, plate_h=7.15)
    bin_ = gridfinity_bin(1, 1, 2)
    seated = 7.15 - BASE_PROFILE_HEIGHT_MM + SEAT_MM
    for x, y in ((-21.0, -21.0), (21.0, 21.0)):
        moved = bin_.val().moved(cq.Location(cq.Vector(x, y, seated)))
        overlap = plate.val().intersect(moved)
        assert (overlap.Volume() if overlap else 0.0) < CONTACT_TOL_MM3


def test_bins_stack_on_the_height_module():
    lower = gridfinity_bin(1, 1, 3)
    upper = gridfinity_bin(1, 1, 2)
    assert _overlap(lower, upper, 3 * HEIGHT_UNIT_MM - SEAT_MM) < CONTACT_TOL_MM3


def test_feet_are_retained_when_offset_from_the_grid():
    """A socket that accepts anything is not a socket: 2 mm off-grid must interfere."""
    plate = gridfinity_baseplate(1, 1, plate_h=7.15)
    feet = gridfinity_feet(1, 1)
    seated = 7.15 - BASE_PROFILE_HEIGHT_MM + SEAT_MM
    moved = feet.val().moved(cq.Location(cq.Vector(2.0, 0, seated)))
    assert plate.val().intersect(moved).Volume() > CONTACT_TOL_MM3


# --- helpers ------------------------------------------------------------------------


def test_dimensions_helper_matches_the_geometry():
    dims = gridfinity_dimensions(2, 1, 3)
    bb = _bbox(gridfinity_bin(2, 1, 3))
    assert dims["width"] == pytest.approx(bb.xlen, abs=0.01)
    assert dims["depth"] == pytest.approx(bb.ylen, abs=0.01)
    assert dims["height"] == pytest.approx(bb.zlen, abs=0.01)
    assert dims["stack_pitch"] == pytest.approx(3 * HEIGHT_UNIT_MM)


def test_units_for_rounds_up_to_a_bin_that_holds_the_object():
    units = gridfinity_units_for(60.0, 20.0, 30.0)
    assert units == {"cols": 2, "rows": 1, "height_u": 6}


# --- wrapper integration -------------------------------------------------------------


def test_bin_script_passes_the_wrapper(tmp_path):
    script = _write(
        tmp_path,
        "bin.py",
        "from blocks import gridfinity_bin\n"
        "result = gridfinity_bin(2, 1, 3, magnet_holes=True, divisions_x=2, "
        "label_tab=True, scoop=True)\n",
    )
    rc, data = run(str(script), "--wall-min", "1.2")
    assert rc == 0, data.get("errors")
    assert data["success"] is True
    assert data["watertight"] is True
    assert data["errors"] == []


def test_baseplate_script_passes_the_wrapper(tmp_path):
    script = _write(
        tmp_path,
        "plate.py",
        "from blocks import gridfinity_baseplate\nresult = gridfinity_baseplate(2, 2)\n",
    )
    rc, data = run(str(script))
    assert rc == 0, data.get("errors")
    assert data["watertight"] is True


# --- conformance check ---------------------------------------------------------------


def test_check_passes_a_standard_bin(tmp_path):
    script = _write(
        tmp_path,
        "good_bin.py",
        "from blocks import gridfinity_bin\nresult = gridfinity_bin(2, 1, 4, divisions_x=2, "
        "label_tab=True)\n",
    )
    issues, detected = run_gridfinity_check(str(script))
    assert issues == []
    det = detected["good_bin"]
    assert det["kind"] == "bin"
    assert (det["cols"], det["rows"]) == (2, 1)
    assert det["height_units"] == 4.0
    assert det["stacking_lip"] is True


def test_check_passes_a_standard_baseplate(tmp_path):
    script = _write(
        tmp_path,
        "good_plate.py",
        "from blocks import gridfinity_baseplate\nresult = gridfinity_baseplate(3, 2)\n",
    )
    issues, detected = run_gridfinity_check(str(script))
    assert issues == []
    assert detected["good_plate"]["kind"] == "baseplate"


def test_check_catches_a_hand_rolled_bin(tmp_path):
    """A plain rounded box on a 42 mm footprint: right idea, no foot, wrong footprint."""
    script = _write(
        tmp_path,
        "naive.py",
        "import cadquery as cq\n"
        "result = (\n"
        "    cq.Workplane('XY').box(42, 42, 21, centered=(True, True, False))\n"
        "    .edges('|Z').fillet(4).faces('>Z').workplane().rect(38, 38).cutBlind(-14)\n"
        ")\n",
    )
    issues, _ = run_gridfinity_check(str(script), kind="bin")
    types = {i["type"] for i in issues}
    assert "gridfinity_footprint" in types
    assert "gridfinity_base_profile" in types
    assert "gridfinity_mate" in types
    assert all(i["severity"] == "error" for i in issues)


def test_check_catches_a_bin_lifted_off_the_bed(tmp_path):
    script = _write(
        tmp_path,
        "floating.py",
        "from blocks import gridfinity_bin\n"
        "result = gridfinity_bin(1, 1, 3).translate((0, 0, 5))\n",
    )
    issues, _ = run_gridfinity_check(str(script))
    assert "gridfinity_bed_offset" in {i["type"] for i in issues}


def test_check_catches_an_off_module_height(tmp_path):
    script = _write(
        tmp_path,
        "tall.py",
        "from blocks import gridfinity_bin\n"
        "result = gridfinity_bin(1, 1, 3).union(\n"
        "    __import__('cadquery').Workplane('XY').workplane(offset=25.4)\n"
        "    .box(20, 20, 3, centered=(True, True, False))\n"
        ")\n",
    )
    issues, _ = run_gridfinity_check(str(script), kind="bin")
    assert "gridfinity_height" in {i["type"] for i in issues}


def test_check_skips_a_script_it_cannot_load(tmp_path):
    script = _write(tmp_path, "broken.py", "raise RuntimeError('boom')\n")
    issues, detected = run_gridfinity_check(str(script))
    assert detected == {}
    assert [i["type"] for i in issues] == ["check_skipped"]
    assert issues[0]["severity"] == "warning"


def test_gate_stage_runs_only_for_gridfinity_parts(tmp_path):
    import quality_gate

    plain = _write(
        tmp_path,
        "plain.py",
        "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)\n",
    )
    assert quality_gate._run_gridfinity_stage(str(plain)) == []

    naive = _write(
        tmp_path,
        "naive_gridfinity.py",
        "import cadquery as cq  # gridfinity bin, hand-modelled\n"
        "result = cq.Workplane('XY').box(42, 42, 21, centered=(True, True, False))\n",
    )
    issues = quality_gate._run_gridfinity_stage(str(naive))
    assert any(i["type"].startswith("gridfinity_") for i in issues)


def test_check_cli_reports_and_exits(tmp_path):
    script = _write(
        tmp_path,
        "cli_bin.py",
        "from blocks import gridfinity_bin\nresult = gridfinity_bin(1, 1, 3)\n",
    )
    env = {**os.environ, "PYTHONPATH": SRC}
    proc = subprocess.run(
        [sys.executable, os.path.join(SRC, "gridfinity_check.py"), "--script", str(script)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["issues"] == []
    assert payload["detected"]["cli_bin"]["cols"] == 1
