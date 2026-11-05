"""script_ops: group layout, commands, preflight refusals, history events (no CadQuery)."""

import json
import os
from pathlib import Path

import pytest
from conftest import REPO_ROOT

import script_history as sh
import script_ops as so

TEMPLATES = Path(REPO_ROOT) / "templates"

PLATE = """from blocks import Part

part = Part("plate")
plate = part.select("box", id="plate")
part.resize(plate)
part.place(plate, op="base")
top = part.param("plate", "h")

standoff = part.select("pcb_standoff", id="standoff")
part.resize(standoff)
part.place(standoff, at=[(x, y, top) for x, y, _ in part.positions("standoff")], op="union")

hole = part.select("cylinder", id="hole")
part.resize(hole)
part.place(hole, at=(0, 0, 0), op="cut")
result = part.result()
"""

EDIT = """from blocks import import_solid

# step: import
result = import_solid(r"C:/in/part.step")

# step: hole
result = result.cut(result.faces(">Z").workplane().hole(5))
"""


def _ops(*argv):
    return so.main([str(a) for a in argv])


def _out(capsys):
    return json.loads(capsys.readouterr().out)


@pytest.fixture
def build(tmp_path):
    d = tmp_path / "build"
    d.mkdir()
    return d


def _script(build, text=PLATE, name="plate.py"):
    path = build / name
    path.write_text(text, encoding="utf-8")
    return path


def _code(build, text):
    path = build / "plate.op.py"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("template", sorted(p.name for p in TEMPLATES.glob("*.py")))
def test_every_template_splits_into_one_group_per_instance(template):
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    lay = so.layout(text)
    assert lay.kind == "step" and lay.text() == text
    assert lay.tail.strip() == "result = part.result()"


def test_l_bracket_groups_keep_their_position_arithmetic():
    lay = so.layout((TEMPLATES / "l_bracket_gusset.py").read_text(encoding="utf-8"))
    assert lay.ids() == ["arm_v", "arm_h", "gusset", "hole_v", "hole_h"]
    assert "x, y, z = part.positions" in lay.get("hole_v")


def test_double_place_and_optional_guard_stay_in_their_group():
    snap = so.layout((TEMPLATES / "lid_snap.py").read_text(encoding="utf-8"))
    assert snap.get("clip").count("part.place(clip") == 2
    box = so.layout((TEMPLATES / "enclosure_body.py").read_text(encoding="utf-8"))
    assert box.ids() == ["body", "boss"] and box.get("boss").lstrip().startswith("if part.has")


def test_marked_and_whole_scripts():
    lay = so.layout(EDIT)
    assert lay.kind == "marked" and lay.ids() == ["import", "hole"] and lay.text() == EDIT
    assert so.layout("x = 1\n").ids() == ["whole"]


def test_replace_changes_only_its_group(build, capsys):
    script = _script(build)
    old = so.layout(PLATE)
    code = _code(
        build,
        'hole = part.select("cylinder", id="hole")\npart.resize(hole)\n'
        'part.place(hole, at=(5, 0, 0), op="cut")\n',
    )
    assert _ops("replace", script, "hole", "--code", code) == 0
    out = _out(capsys)
    assert out["changed_groups"] == ["hole"]
    new = so.layout(script.read_text(encoding="utf-8"))
    assert all(new.get(g) == old.get(g) for g in ("plate", "standoff"))
    assert new.header == old.header and new.tail == old.tail
    assert "(5, 0, 0)" in new.get("hole")
    events = sh._events(script)
    assert events[-1]["event"] == "command" and events[-1]["src"] == out["src"]


def test_insert_and_move_order(build, capsys):
    script = _script(build)
    code = _code(
        build,
        'slot = part.select("box", id="slot")\npart.resize(slot)\npart.place(slot, op="cut")\n',
    )
    assert _ops("insert", script, "--after", "standoff", "--code", code) == 0
    assert so.layout(script.read_text(encoding="utf-8")).ids() == [
        "plate",
        "standoff",
        "slot",
        "hole",
    ]
    assert _ops("move", script, "slot", "--after", "hole") == 0
    assert so.layout(script.read_text(encoding="utf-8")).ids() == [
        "plate",
        "standoff",
        "hole",
        "slot",
    ]


def _refused(script, capsys, *argv):
    before = script.read_bytes()
    assert _ops(*argv) == 1
    assert script.read_bytes() == before
    return _out(capsys)["errors"][0]["type"]


def test_code_for_another_group_is_refused(build, capsys):
    script = _script(build)
    code = _code(build, 'plate = part.select("box", id="plate")\n')
    assert _refused(script, capsys, "replace", script, "hole", "--code", code) == "group_identity"


def test_removing_a_group_a_later_one_depends_on_is_refused(build, capsys):
    script = _script(build)
    assert _refused(script, capsys, "remove", script, "plate") == "undefined_local"


def test_raw_cadquery_in_a_step_group_is_refused(build, capsys):
    script = _script(build)
    code = _code(
        build,
        'hole = part.select("cylinder", id="hole")\n'
        'import cadquery as cq\nx = cq.Workplane("XY").box(10, 10, 2)\n',
    )
    assert _refused(script, capsys, "replace", script, "hole", "--code", code) == "raw_cadquery"


def test_unparsable_code_is_refused(build, capsys):
    script = _script(build)
    code = _code(build, 'hole = part.select("cylinder", id="hole"\n')
    assert _refused(script, capsys, "replace", script, "hole", "--code", code) == "parse_error"


def test_trailing_comment_leaking_into_the_next_group_is_refused(build, capsys):
    script = _script(build)
    code = _code(build, 'standoff = part.select("pcb_standoff", id="standoff")\n# note\n')
    kind = _refused(script, capsys, "replace", script, "standoff", "--code", code)
    assert kind == "scope_violation"


def test_unplanned_instance_is_refused(build, capsys):
    script = _script(build)
    plan = {
        "parts": [
            {"id": "plate", "blocks_needed": [{"id": i} for i in ("plate", "standoff", "hole")]}
        ]
    }
    (build.parent / "BUILD_PLAN.json").write_text(json.dumps(plan), encoding="utf-8")
    code = _code(
        build, 'rib = part.select("box", id="rib")\npart.resize(rib)\npart.place(rib, op="union")\n'
    )
    kind = _refused(script, capsys, "insert", script, "--first", "--code", code)
    assert kind == "unknown_instance"


def test_new_from_template_sets_the_part_id_and_refuses_overwrite(build, capsys):
    script = build / "bracket.py"
    template = TEMPLATES / "l_bracket_gusset.py"
    assert _ops("new", script, "--template", template) == 0
    assert 'Part("bracket")' in script.read_text(encoding="utf-8")
    capsys.readouterr()
    assert _refused(script, capsys, "new", script, "--template", template) == "file_exists"


def test_marked_section_replace(build, capsys):
    script = _script(build, EDIT, "part_edited.py")
    code = _code(
        build, '# step: hole\nresult = result.cut(result.faces(">Z").workplane().hole(6))\n'
    )
    assert _ops("replace", script, "hole", "--code", code) == 0
    new = so.layout(script.read_text(encoding="utf-8"))
    assert new.get("import") == so.layout(EDIT).get("import") and "hole(6)" in new.get("hole")


def test_restore_prev_undoes_a_command(build, capsys, monkeypatch):
    monkeypatch.delenv(sh.SKIP_ENV, raising=False)
    script = _script(build)
    sh.record_run(script, True)
    code = _code(
        build,
        'hole = part.select("cylinder", id="hole")\npart.resize(hole)\n'
        'part.place(hole, at=(5, 0, 0), op="cut")\n',
    )
    assert _ops("replace", script, "hole", "--code", code) == 0
    assert sh.restore(script, "@prev")["success"]
    assert script.read_text(encoding="utf-8") == PLATE


def test_unmanaged_edit_detection(build, capsys):
    script = _script(build)
    assert not sh.unmanaged(script)
    code = _code(
        build,
        'hole = part.select("cylinder", id="hole")\npart.resize(hole)\n'
        'part.place(hole, at=(5, 0, 0), op="cut")\n',
    )
    _ops("replace", script, "hole", "--code", code)
    assert not sh.unmanaged(script)
    script.write_text(script.read_text(encoding="utf-8") + "\n# hand edit\n", encoding="utf-8")
    assert sh.unmanaged(script)
    assert os.path.exists(sh.history_dir(script))
