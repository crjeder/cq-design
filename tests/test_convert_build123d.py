"""Tests for the build123d->CadQuery conversion aid (mapping table + smoke-check)."""

import os
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

from convert_build123d import API_MAPPING, smoke_check  # noqa: E402


def test_mapping_table_entries_have_required_fields():
    assert len(API_MAPPING) > 0
    for entry in API_MAPPING:
        assert entry["b123d"]
        assert entry["cadquery"]
        assert "notes" in entry


def test_mapping_table_covers_box_and_boolean_ops():
    b123d_symbols = {e["b123d"] for e in API_MAPPING}
    assert any("Box" in s for s in b123d_symbols)
    assert any("subtract" in s for s in b123d_symbols)


def test_smoke_check_passes_on_converted_script(tmp_path):
    script = tmp_path / "converted_part.py"
    script.write_text("import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)\n")
    report = smoke_check(str(script), skill_root=os.path.join(SKILL_ROOT, "src"))
    assert report["success"] is True
    assert report["errors"] == []


def test_smoke_check_fails_on_broken_script(tmp_path):
    script = tmp_path / "broken.py"
    script.write_text(
        "import cadquery as cq\ncq.Workplane('XY').box(10, 10, 10).edges('|Z').fillet(99)\n"
    )
    report = smoke_check(str(script), skill_root=os.path.join(SKILL_ROOT, "src"))
    assert report["success"] is False
