"""Tests for the AST-based static pre-flight lint (no CadQuery)."""

import json
import os
import subprocess
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

from script_lint import lint_script  # noqa: E402

SCRIPT_LINT_PATH = os.path.join(SKILL_ROOT, "src", "script_lint.py")


def _write(tmp_path, source: str, name: str = "part.py"):
    p = tmp_path / name
    p.write_text(source)
    return str(p)


def _types(findings):
    return {f.type for f in findings}


def test_clean_script_no_findings(tmp_path):
    source = """
import cadquery as cq

width = 20
depth = 10
height = 2

result = cq.Workplane("XY").box(width, depth, height)
"""
    findings = lint_script(_write(tmp_path, source))
    assert findings == []


def test_boolean_in_loop_positive(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 5)
for i in range(3):
    result = result.cut(cq.Workplane("XY").box(1, 1, 1))
"""
    findings = lint_script(_write(tmp_path, source))
    assert "boolean_in_loop" in _types(findings)


def test_boolean_in_loop_negative(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 5)
for i in range(3):
    pass
result = result.cut(cq.Workplane("XY").box(1, 1, 1))
"""
    findings = lint_script(_write(tmp_path, source))
    assert "boolean_in_loop" not in _types(findings)


def test_missing_result_positive(tmp_path):
    source = """
import cadquery as cq

body = cq.Workplane("XY").box(20, 20, 5)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "missing_result" in _types(findings)


def test_missing_result_negative(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 5)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "missing_result" not in _types(findings)


def test_submodule_import_positive(tmp_path):
    source = """
import cadquery as cq
from blocks.primitives import fillet_box

result = cq.Workplane("XY").box(20, 20, 5)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "submodule_import" in _types(findings)


def test_submodule_import_negative(tmp_path):
    source = """
import cadquery as cq
from blocks import fillet_box

result = cq.Workplane("XY").box(20, 20, 5)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "submodule_import" not in _types(findings)


def test_direct_export_positive(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 5)
cq.exporters.export(result, "part.stl")
"""
    findings = lint_script(_write(tmp_path, source))
    assert "direct_export" in _types(findings)


def test_direct_export_negative(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 5)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "direct_export" not in _types(findings)


def test_magic_number_positive(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 10, 2)
"""
    findings = lint_script(_write(tmp_path, source))
    magic = [f for f in findings if f.type == "magic_number"]
    assert len(magic) == 2  # 20 and 10; the exempt-list literal 2 does not fire


def test_magic_number_negative_named_parameters(tmp_path):
    source = """
import cadquery as cq

width = 20
depth = 10
height = 2

result = cq.Workplane("XY").box(width, depth, height)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "magic_number" not in _types(findings)


def test_unanchored_feature_positive(tmp_path):
    source = """
import cadquery as cq

result = (
    cq.Workplane("XY")
    .box(20, 20, 5)
    .faces(">Z")
    .workplane()
    .center(3, 3)
    .hole(2)
)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "unanchored_feature" in _types(findings)


def test_unanchored_feature_negative_reanchored(tmp_path):
    source = """
import cadquery as cq

result = (
    cq.Workplane("XY")
    .box(20, 20, 5)
    .faces(">Z")
    .workplane()
    .center(3, 3)
    .hole(2)
    .center(0, 0)
    .workplane()
    .hole(2)
)
"""
    findings = lint_script(_write(tmp_path, source))
    # only the first (unre-anchored) hole should trip the check
    unanchored = [f for f in findings if f.type == "unanchored_feature"]
    assert len(unanchored) == 1


def test_unguarded_boolean_positive(tmp_path):
    source = """
import cadquery as cq

width = 20
body = cq.Workplane("XY").box(width, width, 5)
tool = cq.Workplane("XY").box(2, 2, 2).translate((width / 2, 0, 0))
result = body.cut(tool)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "unguarded_boolean" in _types(findings)


def test_unguarded_boolean_negative_guarded(tmp_path):
    source = """
import cadquery as cq
from cq_verify import verify_boolean

width = 20
body = cq.Workplane("XY").box(width, width, 5)
tool = cq.Workplane("XY").box(2, 2, 2).translate((width / 2, 0, 0))
result = verify_boolean(body, body.cut(tool), "cut", "slot")
"""
    findings = lint_script(_write(tmp_path, source))
    assert "unguarded_boolean" not in _types(findings)


def test_shell_after_fillet_positive(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 5).fillet(1).shell(1)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "shell_after_fillet" in _types(findings)


def test_shell_after_fillet_negative(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 5).shell(1).fillet(1)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "shell_after_fillet" not in _types(findings)


def test_fillet_after_chamfer_positive(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 5).edges("|Z").chamfer(1).edges(">Z").fillet(1)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "fillet_after_chamfer" in _types(findings)


def test_fillet_after_chamfer_negative_correct_order(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 5).edges("|Z").fillet(1).edges(">Z").chamfer(1)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "fillet_after_chamfer" not in _types(findings)


def test_fillet_after_chamfer_negative_single_call(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 5).edges("|Z").fillet(1)
"""
    findings = lint_script(_write(tmp_path, source))
    assert "fillet_after_chamfer" not in _types(findings)


def test_syntax_error(tmp_path):
    source = "result = cq.Workplane('XY'.box(20, 20, 5)\n"
    findings = lint_script(_write(tmp_path, source))
    assert len(findings) == 1
    assert findings[0].type == "syntax_error"


def test_finding_shape(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 10, 2)
"""
    findings = lint_script(_write(tmp_path, source))
    assert findings
    for f in findings:
        d = f.to_dict()
        assert isinstance(d["type"], str) and d["type"]
        assert isinstance(d["message"], str) and d["message"]
        assert isinstance(d["hint"], str) and d["hint"]
        assert isinstance(d["line"], int)


def test_cli_clean_script_exit_code(tmp_path):
    source = """
import cadquery as cq

width = 20
result = cq.Workplane("XY").box(width, width, width)
"""
    path = _write(tmp_path, source)
    proc = subprocess.run([sys.executable, SCRIPT_LINT_PATH, path], capture_output=True, text=True)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload == {"success": True, "findings": []}


def test_cli_findings_exit_code(tmp_path):
    source = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 10, 2)
"""
    path = _write(tmp_path, source)
    proc = subprocess.run([sys.executable, SCRIPT_LINT_PATH, path], capture_output=True, text=True)
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["success"] is False
    assert len(payload["findings"]) > 0


def test_corpus_fixture_no_false_positives_beyond_expected(tmp_path):
    """The cq_warehouse fixture uses a direct export call (a true positive) but
    should not trip any of the other, unrelated finding types."""
    fixture = os.path.join(SKILL_ROOT, "tests", "fixtures", "cq_warehouse_fastener.py")
    findings = lint_script(fixture)
    types = _types(findings)
    assert "direct_export" in types
    assert types <= {"direct_export", "magic_number"}


_HOLE_SRC = """
import cadquery as cq

result = cq.Workplane("XY").box(20, 20, 20).faces(">Y").workplane().hole(5)
"""


def test_horizontal_round_hole_flagged(tmp_path):
    assert "horizontal_round_hole" in _types(lint_script(_write(tmp_path, _HOLE_SRC)))


def test_horizontal_round_hole_suppressed_by_teardrop(tmp_path):
    src = _HOLE_SRC + "from blocks import teardrop_bore\n"
    assert "horizontal_round_hole" not in _types(lint_script(_write(tmp_path, src)))


def test_vertical_hole_not_flagged(tmp_path):
    src = _HOLE_SRC.replace(">Y", ">Z")
    assert "horizontal_round_hole" not in _types(lint_script(_write(tmp_path, src)))


# --- step form --------------------------------------------------------------------

STEP_HEAD = "from blocks import Part\n\npart = Part('plate')\n"


def test_step_raw_extrude_rejected_with_primitive_hint(tmp_path):
    src = STEP_HEAD + "import cadquery as cq\nslab = cq.Workplane('XY').box(10, 10, 2)\n"
    findings = [f for f in lint_script(_write(tmp_path, src)) if f.type == "raw_cadquery"]
    lines = {f.line for f in findings}
    assert {4, 5} <= lines
    assert any("`box` primitive" in f.hint for f in findings if f.line == 5)


def test_step_parameters_block_and_resize_args_rejected(tmp_path):
    src = (
        STEP_HEAD
        + "# PARAMETERS\nw = 10\n"
        + "plate = part.select('box', id='plate')\npart.resize(plate, w=10)\n"
    )
    findings = [f for f in lint_script(_write(tmp_path, src)) if f.type == "script_dimension"]
    assert sorted(f.line for f in findings) == [4, 7]


def test_step_position_arithmetic_and_loops_accepted(tmp_path):
    src = STEP_HEAD + (
        "boss = part.select('screw_boss', id='boss')\n"
        "part.resize(boss)\n"
        "top = part.param('plate', 'h')\n"
        "pts = [(x, y, top) for x, y, _ in part.positions('boss')]\n"
        "for i, p in enumerate(pts):\n"
        "    part.place(boss, at=p, rotate=(0, 0, 90 * i), op='union')\n"
        "result = part.result()\n"
    )
    assert lint_script(_write(tmp_path, src)) == []


def test_step_flag_applies_rules_without_part(tmp_path):
    src = "import cadquery as cq\nresult = cq.Workplane('XY').box(1, 2, 3)\n"
    path = _write(tmp_path, src)
    assert "raw_cadquery" not in _types(lint_script(path))
    assert "raw_cadquery" in _types(lint_script(path, step=True))
