import json
import xml.dom.minidom as minidom
from pathlib import Path

import pytest

import concept_sketch as cs

SPEC = {
    "title": "Hook",
    "shapes": [
        {"view": "front", "type": "rect", "x": 0, "y": 0, "w": 60, "h": 40},
        {"view": "front", "type": "circle", "cx": 30, "cy": 20, "r": 5},
        {"view": "top", "type": "polyline", "points": [[0, 0], [60, 0], [60, 20]]},
    ],
    "labels": [{"view": "front", "x": 5, "y": 35, "text": "plate"}],
    "dims": [{"view": "front", "from": [0, -5], "to": [60, -5], "text": "60 mm"}],
}


def test_renders_valid_svg_with_dimension_text():
    svg = cs.render(SPEC)
    minidom.parseString(svg)
    assert "60 mm" in svg and "front" in svg and "top" in svg and "side" not in svg


def test_unknown_shape_and_view_rejected():
    with pytest.raises(cs.SketchError, match="blob"):
        cs.render({"shapes": [{"view": "front", "type": "blob"}]})
    with pytest.raises(cs.SketchError, match="rear"):
        cs.render({"shapes": [{"view": "rear", "type": "line"}]})


def test_cli_exit_codes(tmp_path):
    spec = tmp_path / "concept.json"
    spec.write_text(json.dumps(SPEC), encoding="utf-8")
    assert cs.main([str(spec)]) == 0
    assert (tmp_path / "concept.svg").is_file()
    spec.write_text('{"shapes": []}', encoding="utf-8")
    assert cs.main([str(spec)]) == 1


def test_does_not_import_cadquery():
    assert "cadquery" not in Path(cs.__file__).read_text(encoding="utf-8")
