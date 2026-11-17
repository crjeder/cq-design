"""render_labeled.py: five-view name-labeled preview."""

import json
import subprocess
import sys

import cadquery as cq
import pytest
from PIL import Image

import render_labeled


def _feature(name, x, w=4.0):
    return {
        "name": name,
        "operation": "union",
        "bbox": [x - w / 2, x + w / 2, -2, 2, 10, 14],
        "centroid": [x, 0, 12],
        "volume_mm3": 1.0,
    }


@pytest.fixture
def slab(tmp_path):
    """A 120 x 10 x 10 bar with 11 bumps written as STL, plus a features-file writer."""
    stl = tmp_path / "design.stl"
    bar = cq.Workplane("XY").box(120, 10, 10, centered=(True, True, False))
    for i in range(11):  # one 4 x 4 x 4 bump per feature so every feature owns real faces
        x = -50 + i * 10
        bar = bar.union(
            cq.Workplane("XY").box(4, 4, 4, centered=(True, True, False)).translate((x, 0, 10))
        )
    cq.exporters.export(bar, str(stl))

    def features(items):
        path = tmp_path / "design.features.json"
        path.write_text(json.dumps({"features": items}))
        return str(path)

    return str(stl), features


def test_eleven_features_all_labeled_on_five_panels(slab, tmp_path):
    stl, features = slab
    items = [_feature(f"feat_{i}", -50 + i * 10) for i in range(11)]
    out = tmp_path / "out.png"
    res = render_labeled.render_labeled(stl, features(items), str(out), "bar")
    assert res["labeled"] == [f["name"] for f in items] and res["hidden"] == []
    img = Image.open(out)
    assert img.width == render_labeled.WIDTH and img.height > 2000


def test_feature_outside_part_is_hidden(slab, tmp_path):
    stl, features = slab
    items = [_feature("on_part", 0), _feature("floating", 500)]
    res = render_labeled.render_labeled(stl, features(items), str(tmp_path / "o.png"))
    assert res["labeled"] == ["on_part"] and res["hidden"] == ["floating"]


def test_output_is_deterministic(slab, tmp_path):
    stl, features = slab
    feats = features([_feature("a", -20), _feature("b", 20)])
    render_labeled.render_labeled(stl, feats, str(tmp_path / "1.png"))
    render_labeled.render_labeled(stl, feats, str(tmp_path / "2.png"))
    assert (tmp_path / "1.png").read_bytes() == (tmp_path / "2.png").read_bytes()


def test_no_named_features_still_renders(slab, tmp_path):
    stl, features = slab
    res = render_labeled.render_labeled(stl, features([]), str(tmp_path / "o.png"))
    assert res == {"labeled": [], "hidden": []}


def test_place_never_overlaps_or_leaves_panel():
    placed: list[tuple[float, float, float, float]] = []
    wh = (600, 300)
    for _ in range(6):
        box = render_labeled._place((300, 150), (100, 30), placed, wh)
        assert box is not None
        assert box[0] >= 0 and box[2] <= wh[0] and box[1] >= 0 and box[3] <= wh[1]
        for b in placed:
            assert box[2] <= b[0] or b[2] <= box[0] or box[3] <= b[1] or b[3] <= box[1]
        placed.append(box)


def test_description_from_plan_else_fallback():
    feat = {"name": "slot", "operation": "cut", "bbox": [0, 17, 0, 56, 0, 8.5]}
    assert render_labeled._describe(feat) == "cut, 17 x 56 x 8.5 mm"
    vocab = render_labeled.build_vocabulary([feat], {"slot": {"description": "cable slot"}})
    assert render_labeled._describe(vocab[0]) == "cable slot"


def test_plan_interfaces_are_fallback_vocabulary_only_when_no_stages():
    itf = {"p": {"name": "p", "position_mm": [1, 2, 3], "description": "d"}}
    assert [f["name"] for f in render_labeled.build_vocabulary([], itf)] == ["p"]
    assert render_labeled.build_vocabulary([_feature("a", 0)], itf)[0]["name"] == "a"
    assert len(render_labeled.build_vocabulary([_feature("a", 0)], itf)) == 1


def test_no_opengl_import():
    code = "import render_labeled, sys; print(any(m in sys.modules for m in ('pyrender','OpenGL')))"
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd="src"
    ).stdout
    assert out.strip() == "False"
