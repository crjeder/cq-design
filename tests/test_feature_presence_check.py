"""Tests for feature_presence_check.py (declared-feature presence assertion).

Runs real CadQuery scripts through the cut/union recording hook, so each test takes a
couple of seconds.
"""

from feature_presence_check import run_feature_presence_check

# Body with a port-cutout-shaped tool cut at center (10, 0, 15), extents (9, 4, 3).
BODY_WITH_PORT = (
    "import cadquery as cq\n"
    "result = (cq.Workplane('XY').box(40, 30, 30)\n"
    "          .cut(cq.Workplane('XY').box(9, 4, 3).translate((10, 0, 15))))\n"
)
# Same body, no cutout.
BODY_NO_PORT = "import cadquery as cq\nresult = cq.Workplane('XY').box(40, 30, 30)\n"


def _script(tmp_path, name, body):
    p = tmp_path / f"{name}.py"
    p.write_text(body)
    return str(p)


def _plan(interfaces):
    return {"parts": [{"id": "body", "interfaces": interfaces}]}


def test_declared_feature_present_passes(tmp_path):
    script = _script(tmp_path, "body", BODY_WITH_PORT)
    plan = _plan([{"type": "port_cutout", "position_mm": [10, 0, 15], "size_mm": [9, 4]}])
    assert run_feature_presence_check(plan, script) == []


def test_declared_feature_absent_errors(tmp_path):
    script = _script(tmp_path, "body", BODY_NO_PORT)
    plan = _plan([{"type": "port_cutout", "position_mm": [10, 0, 15], "size_mm": [9, 4]}])
    issues = run_feature_presence_check(plan, script)
    assert len(issues) == 1
    assert issues[0]["severity"] == "error"
    assert issues[0]["type"] == "feature_absent"
    assert issues[0]["part"] == "body"
    assert issues[0]["position_mm"] == [10.0, 0.0, 15.0]


def test_feature_off_position_warns(tmp_path):
    script = _script(tmp_path, "body", BODY_WITH_PORT)  # built at (10, 0, 15)
    plan = _plan([{"type": "port_cutout", "position_mm": [10, 0, 17]}])  # declared 2 mm off
    issues = run_feature_presence_check(plan, script)
    assert len(issues) == 1
    assert issues[0]["severity"] == "warning"
    assert issues[0]["type"] == "feature_drift"
    assert issues[0]["built_position_mm"] == [10.0, 0.0, 15.0]


def test_feature_wrong_size_warns(tmp_path):
    script = _script(tmp_path, "body", BODY_WITH_PORT)  # extents (9, 4, 3)
    plan = _plan([{"type": "port_cutout", "position_mm": [10, 0, 15], "size_mm": [9, 12]}])
    issues = run_feature_presence_check(plan, script)
    assert len(issues) == 1
    assert issues[0]["type"] == "feature_drift"
    assert issues[0]["declared_size_mm"] == [9.0, 12.0]


def test_non_allowlisted_type_skipped_not_absent(tmp_path):
    script = _script(tmp_path, "body", BODY_WITH_PORT)
    plan = _plan([{"type": "snap_fit", "position_mm": [10, 0, 15]}])
    issues = run_feature_presence_check(plan, script)
    assert len(issues) == 1
    assert issues[0]["type"] == "check_skipped"
    assert issues[0]["severity"] == "warning"


def test_interface_without_position_no_finding(tmp_path):
    script = _script(tmp_path, "body", BODY_WITH_PORT)
    plan = _plan([{"type": "port_cutout"}])
    assert run_feature_presence_check(plan, script) == []
