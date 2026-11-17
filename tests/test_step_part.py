"""Probes, the probe registry, plan-derived probes, and the eager `Part` step recorder."""

import json
import math
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


def _part(blocks, interfaces=(), dims=(40, 30, 10), probes=None):
    part = {
        "id": "plate",
        "description": "Plate with a screw boss",
        "dimensions": dict(zip(("w_mm", "d_mm", "h_mm"), dims, strict=True)),
        "interfaces": list(interfaces),
        "blocks_needed": list(blocks),
    }
    if probes is not None:
        part["probes"] = list(probes)
    return part


@pytest.fixture
def plan(tmp_path, monkeypatch):
    def _write(blocks=(PLATE, BOSS), interfaces=(), dims=(40, 30, 10), probes=None):
        path = tmp_path / "BUILD_PLAN.json"
        path.write_text(json.dumps(minimal_plan([_part(blocks, interfaces, dims, probes)])))
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


def test_authored_probes_seed_the_registry():
    hole = {"kind": "empty_at", "p": [0, 0, 2], "label": "M3 hole at center"}
    rib = {"kind": "solid_at", "p": [15, 10, 2], "label": "rib", "instance": "rib"}
    probes, _ = pr.plan_probes(_part([], dims=(40, 30, 4), probes=[hole, rib]))
    assert probes[-2].p == (0, 0, 2) and probes[-2].label == "M3 hole at center"
    reg = pr.Registry()
    reg.add(probes, "plan")
    box = cq.Workplane("XY").box(40, 30, 4, centered=(True, True, False))
    _, failed = reg.check(box.val(), final=True)
    assert [f["label"] for f in failed] == ["M3 hole at center"]
    assert reg.check(box.faces(">Z").hole(5).val(), final=True) == (3, [])
    assert reg.check(box.val())[0] == 1
    assert reg.check(box.val(), armed={"rib"})[0] == 2


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
    assert result.findSolid().Volume() == pytest.approx(hand.findSolid().Volume(), rel=1e-6)
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
    assert bore[0].p == pytest.approx((10, 5, 8.5))


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
    plug = {"name": "cylinder", "id": "plug", "params": {"d": 3, "h": 6}}
    m1 = {
        "type": "screw_mount",
        "name": "m1",
        "instance": "boss",
        "position_mm": [10, 5, 8.5],
        "diameter_mm": 3.2,
    }
    plan(blocks=[PLATE, BOSS, plug], interfaces=[m1])
    part = Part("plate")
    plate = part.select("box", id="plate")
    part.resize(plate)
    part.place(plate, op="base")  # m1 is not armed until the boss step
    boss = part.select("screw_boss", id="boss")
    part.resize(boss)
    part.place(boss, at=(10, 5, 4), op="union")
    filler = part.select("cylinder", id="plug")
    part.resize(filler)
    with pytest.raises(RuntimeError, match="probe_failed.*m1"):
        part.place(filler, at=(10, 5, 4), op="union")


def test_plan_probe_without_instance_is_checked_at_result(plan):
    m1 = {"type": "screw_mount", "name": "m1", "position_mm": [0, 0, 2], "diameter_mm": 3}
    plan(blocks=[PLATE], interfaces=[m1])
    part = Part("plate")
    plate = part.select("box", id="plate")
    part.resize(plate)
    part.place(plate, op="base")
    with pytest.raises(RuntimeError, match="probe_failed.*m1"):
        part.result()


def test_authored_probe_fails_at_result(plan):
    plan(blocks=[PLATE], probes=[{"kind": "empty_at", "p": [0, 0, 2], "label": "M3 hole"}])
    part = Part("plate")
    plate = part.select("box", id="plate")
    part.resize(plate)
    part.place(plate, op="base")
    with pytest.raises(RuntimeError, match="probe_failed.*M3 hole"):
        part.result()


def test_authored_probe_point_changes_step_key(plan):
    probe = {"kind": "empty_at", "p": [0, 0, 2], "label": "M3 hole"}
    plan(probes=[probe])
    key = Part("plate").key
    plan(probes=[{**probe, "p": [0, 0, 3]}])
    assert Part("plate").key != key


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


# --- print-pose finishing ------------------------------------------------------------

SLAB = {"name": "box", "id": "plate", "params": {"w": 20, "d": 10, "h": 5}}


def _slab(plan, monkeypatch, rotate, edges, interfaces=(), extra=(), dims=(20, 10, 5)):
    plan(blocks=[{**SLAB, "edges": edges}, *extra], interfaces=interfaces, dims=dims)
    if rotate is None:
        monkeypatch.delenv("CQ_PRINT_ROTATE", raising=False)
    else:
        monkeypatch.setenv("CQ_PRINT_ROTATE", json.dumps(rotate))
    part = Part("plate")
    plate = part.select("box", id="plate")
    part.resize(plate)
    part.place(plate, op="base")
    return part


def test_step_loop_leaves_edges_untreated(plan, monkeypatch):
    part = _slab(plan, monkeypatch, None, {"vertical": 1.0})
    assert part.result().findSolid().Volume() == pytest.approx(1000)


def test_upright_vertical_edges_are_filleted(plan, monkeypatch):
    part = _slab(plan, monkeypatch, [], {"vertical": 1.0})
    removed = 1000 - part.result().findSolid().Volume()
    assert removed == pytest.approx(4 * (1 - math.pi / 4) * 5, rel=1e-3)


def test_rotated_pose_chamfers_build_vertical_edges(plan, monkeypatch):
    part = _slab(plan, monkeypatch, [{"axis": "X", "angle_deg": 90}], {"vertical": 1.0})
    removed = 1000 - part.result().findSolid().Volume()
    assert removed == pytest.approx(4 * 0.5 * 5, rel=1e-3)


def test_chamfer_breaking_a_plan_probe_fails(plan, monkeypatch):
    rim = {
        "type": "union",
        "name": "rim",
        "instance": "plate",
        "position_mm": [9.6, 0, 4.6],
        "diameter_mm": 1,
    }
    part = _slab(plan, monkeypatch, [], {"top_outer": 2.0}, interfaces=[rim])
    with pytest.raises(RuntimeError, match="finishing_probe_failed.*rim"):
        part.result()


def test_lost_edge_set_fails(plan, monkeypatch):
    skim = {"name": "box", "id": "skim", "params": {"w": 30, "d": 20, "h": 2}}
    part = _slab(plan, monkeypatch, [], {"top_outer": 0.5}, extra=[skim], dims=(20, 10, 4.6))
    cut = part.select("box", id="skim")
    part.resize(cut)
    part.place(cut, at=(0, 0, 4.6), op="cut")
    with pytest.raises(RuntimeError, match=r"finishing_probe_failed.*plate\.top_outer"):
        part.result()


def test_pair_block_members_place_into_their_unions(plan):
    hinge = {
        "name": "pin_hinge",
        "id": "hinge",
        "params": {"length": 40, "knuckles": 5, "leaf_w": 15, "leaf_t": 3},
    }
    plan(blocks=[hinge], dims=(34.05, 40, 4.05))
    part = Part("plate")
    h = part.select("pin_hinge", id="hinge")
    part.resize(h)
    with pytest.raises(RuntimeError, match="member must name one of"):
        part.place(h, op="base")
    part.place(h, op="base", member="leaf_a", into="leaf_a")
    part.place(h, op="base", member="leaf_b", into="leaf_b")
    result = part.result()
    assert isinstance(result, dict) and sorted(result) == ["leaf_a", "leaf_b"]
    assert {p.label for p in part.registry.probes if p.owner != "plan"} == {
        "leaf_a",
        "leaf_b",
        "pin bore",
    }


def test_auto_print_up_resolves_to_the_pose(plan, monkeypatch):
    bore = {
        "name": "teardrop_bore",
        "id": "bore",
        "params": {"d": 5, "depth": 10, "print_up": "auto"},
    }
    plan(blocks=[bore])
    monkeypatch.setenv("CQ_PRINT_ROTATE", json.dumps([{"axis": "X", "angle_deg": 180}]))
    part = Part("plate")
    handle = part.resize(part.select("teardrop_bore", id="bore"))
    assert handle.params is not None
    assert handle.params["print_up"] == pytest.approx((0, 0, -1), abs=1e-9)


# --- interface area of union steps ----------------------------------------------------


def _union_step(part):
    return next(st for st in part.steps if st["kind"] == "place" and st["op"] == "union")


def test_union_records_interface_area(plan):
    plan()
    part, _ = _build()
    step = _union_step(part)
    assert step["interface"]["area_mm2"] > 4.0
    assert step["interface"]["location_xyz_mm"][2] == pytest.approx(4, abs=0.5)


def test_small_interface_fails_the_step(plan):
    thin = {**BOSS, "params": {"d_screw": 0.5, "d_outer": 1.5, "h": 6}}
    plan(blocks=[PLATE, thin])
    with pytest.raises(RuntimeError, match=r"small_interface.*interface_min_area_mm2 4\.0") as e:
        _build()
    assert "build plate" in str(e.value)
    assert Part.last is not None
    err = Part.last.steps[-1]["error"]
    assert err["type"] == "small_interface"
    assert err["area_mm2"] < 4.0 and err["threshold_mm2"] == 4.0 and err["instance"] == "boss"


def test_interface_constraint_comes_from_the_plan(plan, tmp_path):
    thin = {**BOSS, "params": {"d_screw": 0.5, "d_outer": 1.5, "h": 6}}
    path = plan(blocks=[PLATE, thin])
    data = json.loads(path.read_text())
    data["constraints"]["interface_min_area_mm2"] = 0.5
    path.write_text(json.dumps(data))
    assert _union_step(_build()[0])["interface"]["area_mm2"] > 0.5


def test_each_copy_is_measured_on_its_own(plan):
    plan()
    part = Part("plate")
    plate = part.select("box", id="plate")
    part.resize(plate)
    part.place(plate, op="base")
    boss = part.select("screw_boss", id="boss")
    part.resize(boss)
    part.place(boss, at=[(10, 5, 4), (-10, -5, 4)], op="union")
    copies = part.steps[-1]["interface"]["copies_mm2"]
    assert len(copies) == 2 and min(copies) > 4.0


def test_cut_and_base_steps_have_no_interface(plan):
    plan()
    part, _ = _build()
    base = next(st for st in part.steps if st["kind"] == "place" and st["op"] == "base")
    assert "interface" not in base


def test_cached_union_step_keeps_its_interface(plan):
    plan()
    Part.cache = {}
    try:
        first = _union_step(_build()[0])["interface"]
        second_part = _build()[0]
    finally:
        Part.cache = None
    again = _union_step(second_part)
    assert again.get("cached") and again["interface"] == first
