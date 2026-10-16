"""Tests for edge_treatment_check.py (Chamfer / Fillet rule enforcement).

Runs real CadQuery scripts through the fillet/chamfer recording hook, so each test
takes a couple of seconds.
"""

import pytest

from edge_treatment_check import run_edge_treatment_check


def _script(tmp_path, name, body):
    p = tmp_path / f"{name}.py"
    p.write_text(body)
    return str(p)


def _plan(*ids):
    return {"parts": [{"id": i} for i in ids]}


def _identity(*uids):
    """Orientations map stating each union's print pose equals its build pose."""
    return {uid: {"rotate": []} for uid in uids}


@pytest.mark.parametrize(
    "script_name, part_id, body",
    [
        (
            "body",
            "body",
            "import cadquery as cq\n"
            "result = cq.Workplane('XY').box(20, 20, 10)"
            ".edges('|Z').fillet(2).edges('|X or |Y').chamfer(1)\n",
        ),
        (
            "orphan",
            "something_else",
            "import cadquery as cq\n"
            "result = cq.Workplane('XY').box(10, 10, 10).edges('|Z').chamfer(1)\n",
        ),
    ],
    ids=["compliant_part", "unknown_script"],
)
def test_no_findings(tmp_path, script_name, part_id, body):
    """No findings when the treatment follows the rule, or the script's part id is unknown."""
    script = _script(tmp_path, script_name, body)
    assert run_edge_treatment_check(_plan(part_id), script, _identity(script_name)) == []


def test_no_edge_treatment_returns_empty(tmp_path):
    """A part that applies no fillet/chamfer at all produces no findings."""
    script = _script(
        tmp_path, "plain", "import cadquery as cq\nresult = cq.Workplane('XY').box(20, 20, 10)\n"
    )
    assert run_edge_treatment_check(_plan("plain"), script, {}) == []


def test_chamfered_vertical_edge_is_flagged(tmp_path):
    """Chamfering a vertical edge should recommend a fillet."""
    script = _script(
        tmp_path,
        "bad",
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(20, 20, 10).edges('|Z').chamfer(2)\n",
    )
    issues = run_edge_treatment_check(_plan("bad"), script, _identity("bad"))
    assert len(issues) == 1
    issue = issues[0]
    assert issue["severity"] == "warning"
    assert issue["type"] == "edge_treatment"
    assert issue["applied"] == "chamfer"
    assert issue["recommended"] == "fillet"
    assert issue["edge_orientation"] == "vertical"
    assert issue["count"] == 4


@pytest.mark.parametrize(
    "script_name, body",
    [
        (
            "bad",
            "import cadquery as cq\n"
            "result = cq.Workplane('XY').box(20, 20, 10).edges('|X').fillet(1)\n",
        ),
        (
            "rim",
            "import cadquery as cq\n"
            "result = cq.Workplane('XY').circle(10).extrude(15).edges('>Z').fillet(2)\n",
        ),
    ],
    ids=["straight_edge", "round_rim"],
)
def test_filleted_horizontal_edge_is_flagged(tmp_path, script_name, body):
    """Filleting a horizontal edge (straight or a round rim) should recommend a chamfer."""
    script = _script(tmp_path, script_name, body)
    issues = run_edge_treatment_check(_plan(script_name), script, _identity(script_name))
    assert len(issues) == 1
    assert issues[0]["applied"] == "fillet"
    assert issues[0]["recommended"] == "chamfer"
    assert issues[0]["edge_orientation"] == "horizontal"


def test_orientation_transform_reclassifies_edge(tmp_path):
    """A filleted authored-vertical edge is compliant under identity but flagged once the
    print orientation rotates it into the bed plane."""
    script = _script(
        tmp_path,
        "rotpart",
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(20, 20, 10).edges('|Z').fillet(2)\n",
    )
    plan = _plan("rotpart")

    assert run_edge_treatment_check(plan, script, _identity("rotpart")) == []

    rotated = {
        "rotpart": {
            "rotate": [
                {"axis": "X", "angle_deg": 90},
                {"axis": "Y", "angle_deg": 0},
                {"axis": "Z", "angle_deg": 0},
            ]
        }
    }
    issues = run_edge_treatment_check(plan, script, rotated)
    assert len(issues) == 1
    assert issues[0]["recommended"] == "chamfer"
    assert issues[0]["edge_orientation"] == "horizontal"


def test_multi_union_attributes_to_correct_union(tmp_path):
    """A violating treatment is reported under the union it belongs to, not its sibling."""
    script = _script(
        tmp_path,
        "twopart",
        "import cadquery as cq\n"
        "a = cq.Workplane('XY').box(10, 10, 10).edges('|Z').chamfer(1)\n"
        "b = cq.Workplane('XY').box(10, 10, 10).translate((50, 0, 0))\n"
        "result = {'a': a, 'b': b}\n",
    )
    plan = {"parts": [{"id": "twopart", "unions": [{"id": "a"}, {"id": "b"}]}]}
    issues = run_edge_treatment_check(plan, script, _identity("a", "b"))
    assert len(issues) == 1
    assert issues[0]["union"] == "a"


def test_missing_orientation_skips_instead_of_authored_frame(tmp_path):
    """A treated union with no print orientation is skipped (the rule is bed-relative), not
    judged in the build pose."""
    script = _script(
        tmp_path,
        "bad",
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(20, 20, 10).edges('|Z').chamfer(2)\n",
    )
    issues = run_edge_treatment_check(_plan("bad"), script, {})
    assert len(issues) == 1
    assert issues[0]["type"] == "check_skipped"
    assert issues[0]["union"] == "bad"
    assert not any(i["type"] == "edge_treatment" for i in issues)
