import os

import cadquery as cq
from conftest import run_wrapper

import section_select
from render_preview import _section_cuts

HOLE_SCRIPT = (
    "import cadquery as cq\n"
    "result = cq.Workplane('XY').box(60,40,10).faces('>Z').workplane().center(10,5).hole(5)\n"
)


def holed_box(*holes):
    wp = cq.Workplane("XY").box(60, 40, 10)
    for x, y in holes:
        wp = wp.cut(cq.Workplane("XY").center(x, y).circle(2).extrude(20, both=True))
    return wp


def test_auto_cut_replaces_center_fallback():
    assert _section_cuts(holed_box((10, 5)), [], True, True) == [("x", 10, False)]


def test_extra_sections_reserve_slots():
    holes = [(-25 + 7 * i, -18 + 5 * i) for i in range(8)]
    cuts = _section_cuts(holed_box(*holes), [("y", 0.0)], False, True)
    assert cuts[0] == ("y", 0.0, False) and len(cuts) == 3


def test_full_extra_sections_skip_selector(monkeypatch, capsys):
    monkeypatch.setattr(section_select, "select_sections", lambda *a: 1 / 0)
    extra = [("x", 1.0), ("y", 2.0), ("z", 3.0)]
    assert _section_cuts(holed_box((10, 5)), extra, False, True) == [(*c, False) for c in extra]
    assert capsys.readouterr().err == ""


def test_plain_box_falls_back_to_centers():
    cuts = _section_cuts(cq.Workplane("XY").box(10, 10, 10), [], False, True)
    assert [c[2] for c in cuts] == [True, True, True]


def test_selector_error_only_warns(monkeypatch, capsys):
    monkeypatch.setattr(section_select, "select_sections", lambda *a: 1 / 0)
    cuts = _section_cuts(holed_box((10, 5)), [], False, True)
    assert len(cuts) == 3 and all(c[2] for c in cuts)
    assert "--auto-sections failed" in capsys.readouterr().err


def test_multi_union_sees_every_union():
    combined = cq.Workplane("XY").box(10, 10, 10).add(holed_box((10, 5)).translate((50, 0, 0)))
    assert _section_cuts(combined, [], False, True) == [("x", 60, False)]


def test_wrapper_forwards_flag(tmp_path):
    script = tmp_path / "holed.py"
    script.write_text(HOLE_SCRIPT)
    rc, data = run_wrapper(script, "--preview", "--auto-sections")
    assert rc == 0, data.get("stderr")
    names = [os.path.basename(p) for p in data["previews"][1:]]
    assert names == ["holed_preview_section_x_10mm.png"]
