"""Probes, the probe registry, plan-derived probes, and the eager `Part` step recorder."""

import json
import runpy

import cadquery as cq
import pytest
from conftest import minimal_plan

import probes as pr
from blocks import Part
from plan import run as import_params
from plan import validate_plan

PLATE = {"name": "box", "id": "plate", "params": {"w": 40, "d": 30, "h": 4}}
BOSS = {"name": "screw_boss", "id": "boss", "params": {"d_screw": 3.2, "d_outer": 8, "h": 6}}


def _part(blocks, interfaces=()):
    return {
        "id": "plate",
        "description": "Plate with a screw boss",
        "dimensions": {"w_mm": 40, "d_mm": 30, "h_mm": 10},
        "interfaces": list(interfaces),
        "blocks_needed": list(blocks),
    }


@pytest.fixture
def plan(tmp_path, monkeypatch):
    def _write(blocks=(PLATE, BOSS), interfaces=()):
        path = tmp_path / "BUILD_PLAN.json"
        path.write_text(json.dumps(minimal_plan([_part(blocks, interfaces)])))
        monkeypatch.setenv("CQ_PLAN", str(path))
        return path

    return _write


# --- probe kinds -------------------------------------------------------------------


def test_point_ray_and_bbox_probes_on_a_bored_block():
    body = cq.Workplane("XY").box(20, 20, 10, centered=(True, True, False)).faces(">Z").hole(5)
    shape = body.val()
    assert pr.evaluate(pr.solid_at((7, 7, 5)), shape)[0]
    assert pr.evaluate(pr.empty_at((0, 0, 5)), shape)[0]
    assert not pr.evaluate(pr.solid_at((0, 0, 5)), shape)[0]
    assert pr.evaluate(pr.ray((0, 0, 5), (0, 0, 1), 0), shape) == (True, 0)
    assert pr.evaluate(pr.ray((7, 7, 5), (0, 0, 1), 2), shape) == (True, 2)
    assert pr.evaluate(pr.bbox((-10, -10, 0), (10, 10, 10)), shape)[0]
    assert pr.evaluate(pr.bbox(size=(30, 30, 12), mode="within"), shape)[0]
    assert not pr.evaluate(pr.bbox(size=(30, 30, 12)), shape)[0]


def test_blind_bore_fails_the_through_ray():
    body = cq.Workplane("XY").box(20, 20, 10, centered=(True, True, False)).faces(">Z").hole(5, 6)
    ok, hits = pr.evaluate(pr.ray((0, 0, 5), (0, 0, 1), 0), body.val())
    assert not ok and hits == 2


def test_face_distance():
    shape = cq.Workplane("XY").box(10, 10, 10).val()
    assert pr.face_distance(shape, (0, 0, 0)) == pytest.approx(5)
    assert pr.face_distance(shape, (0, 0, 4.9)) == pytest.approx(0.1)


def test_transform_rotates_then_translates():
    moved = pr.transform(pr.ray((1, 0, 0), (1, 0, 0), 0), at=(10, 0, 0), rotate=(0, 0, 90))
    assert moved.p == pytest.approx((10, 1, 0))
    assert moved.dir == pytest.approx((0, 1, 0))


# --- registry ------------------------------------------------------------------------


def test_registry_retires_block_probes_inside_a_tool_but_never_plan_probes():
    reg = pr.Registry()
    reg.add([pr.solid_at((0, 0, 1))], owner=1)
    reg.add([pr.empty_at((0, 0, 1))], owner="plan")
    tool = cq.Workplane("XY").box(4, 4, 4).val()
    gone = reg.retire_inside(tool, step=2)
    assert [p.owner for p in gone] == [1]
    assert [p.owner for p in reg.probes] == ["plan"]


# --- plan-derived probes -------------------------------------------------------------


def test_plan_probes_from_interfaces():
    part = _part(
        [],
        [
            {"type": "screw_mount", "name": "m1", "position_mm": [10, 10, 0], "diameter_mm": 3.2},
            {
                "type": "clearance_opening",
                "name": "bore",
                "wall": "top",
                "position_mm": [0, 0, 5],
                "diameter_mm": 20,
            },
            {"type": "union", "name": "post", "position_mm": [5, 5, 8], "diameter_mm": 6},
            {"type": "face_mount", "name": "seat", "position_mm": [0, 0, 0], "size_mm": [10, 10]},
            {"type": "screw_mount", "name": "loose"},
        ],
    )
    probes, unprobed = pr.plan_probes(part)
    kinds = [(p.kind, p.label) for p in probes]
    assert ("bbox", "envelope") in kinds
    assert ("empty_at", "m1") in kinds
    assert ("empty_at", "bore") in kinds and ("ray", "bore") in kinds
    assert ("solid_at", "post") in kinds
    assert unprobed == ["seat", "loose"]


# --- Part: plan binding --------------------------------------------------------------


def _build(boss_at=(10, 5, 4)):
    part = Part("plate")
    plate = part.select("box", id="plate")
    part.resize(plate)
    part.place(plate, op="base")
    boss = part.select("screw_boss", id="boss")
    part.resize(boss)
    part.place(boss, at=boss_at, op="union")
    return part, part.result()


def test_part_matches_hand_built_workplane(plan):
    plan()
    part, result = _build()
    hand = (
        cq.Workplane("XY")
        .box(40, 30, 4, centered=(True, True, False))
        .union(cq.Workplane("XY").circle(4).extrude(6).faces(">Z").hole(3.2).translate((10, 5, 4)))
    )
    assert result.val().Volume() == pytest.approx(hand.val().Volume(), rel=1e-6)
    assert result.val().BoundingBox().zmax == pytest.approx(10)
    assert [s["kind"] for s in part.steps] == [
        "select",
        "resize",
        "place",
        "select",
        "resize",
        "place",
        "result",
    ]
    assert part.steps[4]["args"] == BOSS["params"]


def test_boss_probes_follow_placement(plan):
    plan()
    part, _ = _build()
    bore = [p for p in part.registry.probes if p.label == "bore"]
    assert bore[0].p == pytest.approx((10, 5, 7))


def test_select_missing_instance_names_planned_ids(plan):
    plan()
    with pytest.raises(RuntimeError, match=r"step_plan.*'rib'.*\['boss', 'plate'\]"):
        Part("plate").select("box", id="rib")


def test_resize_rejects_misspelled_param(plan):
    plan(blocks=[PLATE, {**BOSS, "params": {"d_scew": 3.2, "d_outer": 8, "h": 6}}])
    part = Part("plate")
    match = r"unknown params \['d_scew'\].*missing params \['d_screw'\]"
    with pytest.raises(RuntimeError, match=match):
        part.resize(part.select("screw_boss", id="boss"))


def test_floating_union_fails_on_solid_count(plan):
    plan()
    with pytest.raises(RuntimeError, match="probe_failed.*2 solids"):
        _build(boss_at=(10, 5, 4.5))


def test_union_filling_a_plan_bore_fails(plan):
    plan(
        interfaces=[
            {"type": "screw_mount", "name": "m1", "position_mm": [10, 5, 7], "diameter_mm": 3.2}
        ]
    )
    _build()  # the boss bore is open at the plan position
    part = Part("plate")
    plate = part.select("box", id="plate")
    part.resize(plate)
    part.place(plate, op="base")
    plug = part.select("box", id="plate")
    part.resize(plug)
    with pytest.raises(RuntimeError, match="probe_failed.*m1"):
        part.place(plug, at=(10, 5, 4), op="union")


def test_cut_retires_overlapped_block_probe(plan):
    plan(blocks=[PLATE, BOSS, {"name": "cylinder", "id": "cbore", "params": {"d": 7, "h": 3}}])
    part = Part("plate")
    plate = part.select("box", id="plate")
    part.resize(plate)
    part.place(plate, op="base")
    boss = part.select("screw_boss", id="boss")
    part.resize(boss)
    part.place(boss, at=(10, 5, 4), op="union")
    cbore = part.select("cylinder", id="cbore")
    part.resize(cbore)
    part.place(cbore, at=(10, 5, 6.5), op="cut")
    step = part.steps[-1]
    assert step["ok"] and "wall" in [r["label"] for r in step["probes"]["retired"]]


def test_plan_edit_changes_geometry_with_script_unchanged(plan, tmp_path):
    path = plan()
    script = tmp_path / "plate.py"
    script.write_text(
        "from blocks import Part\n"
        "part = Part('plate')\n"
        "plate = part.select('box', id='plate')\n"
        "part.resize(plate)\n"
        "part.place(plate, op='base')\n"
        "boss = part.select('screw_boss', id='boss')\n"
        "part.resize(boss)\n"
        "part.place(boss, at=(10, 5, part.param('plate', 'h')), op='union')\n"
        "result = part.result()\n"
    )
    assert runpy.run_path(str(script))["result"].val().BoundingBox().zmax == pytest.approx(10)
    data = json.loads(path.read_text())
    data["parts"][0]["blocks_needed"][1]["params"]["h"] = 5
    data["parts"][0]["dimensions"]["h_mm"] = 9
    path.write_text(json.dumps(data))
    assert runpy.run_path(str(script))["result"].val().BoundingBox().zmax == pytest.approx(9)


def test_positions_come_from_interfaces(plan):
    plan(
        interfaces=[
            {"type": "screw_mount", "name": f"m{i}", "instance": "boss", "position_mm": [x, 0, 4]}
            for i, x in enumerate((-10, 10))
        ]
    )
    assert Part("plate").positions("boss") == [(-10, 0, 4), (10, 0, 4)]


# --- plan validation and import-params ------------------------------------------------


def _validate(tmp_path, blocks, interfaces=()):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(minimal_plan([_part(blocks, interfaces)])))
    return validate_plan(str(path))


def test_instance_with_complete_params_validates(tmp_path):
    assert _validate(tmp_path, [BOSS]) == []


def test_unknown_edge_set_fails(tmp_path):
    errors = _validate(tmp_path, [{**PLATE, "edges": {"rim": 1.0}}])
    assert any("'plate'" in e and "'rim'" in e and "edge sets" in e for e in errors)


def test_missing_required_param_fails(tmp_path):
    errors = _validate(tmp_path, [{"name": "cylinder", "id": "post", "params": {"d": 5}}])
    assert any("'post'" in e and "['h']" in e for e in errors)


def test_interface_instance_must_be_planned(tmp_path):
    errors = _validate(tmp_path, [BOSS], [{"type": "screw_mount", "instance": "nope"}])
    assert any("'nope'" in e for e in errors)


def test_import_params_not_applicable_for_step_script(tmp_path):
    script = tmp_path / "plate.py"
    script.write_text("from blocks import Part\npart = Part('plate')\n")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(minimal_plan([_part([PLATE])])))
    before = plan_path.read_text()
    report = import_params(str(script), "plate", str(plan_path), write=True)
    assert report["status"] == "not_applicable" and report["errors"] == []
    assert plan_path.read_text() == before
