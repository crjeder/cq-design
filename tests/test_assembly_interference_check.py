"""Tests for the all-pairs rest-pose interference stage (trimesh box STLs, no CadQuery)."""

from conftest import box_stl

from assembly_interference_check import run_assembly_interference_check


def _plan(parts, joints=None):
    plan = {"parts": parts}
    if joints:
        plan["joints"] = joints
    return plan


def _hits(issues):
    return [i for i in issues if i["type"] == "assembly_interference"]


def _joint(clearance, part_a="a", part_b="b"):
    return {
        "joint_id": "j1",
        "block": "dowel",
        "params": {"clearance": clearance},
        "members": [
            {"member": "m1", "part": part_a},
            {"member": "m2", "part": part_b},
        ],
    }


def test_sunk_lid_flagged(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))  # x in [-5, 5]
    box_stl(tmp_path / "b.stl", (9, 0, 0))  # x in [4, 14] -> 1 mm deep, 100 mm^3
    issues = run_assembly_interference_check(_plan([{"id": "a"}, {"id": "b"}]), str(tmp_path))
    hits = _hits(issues)
    assert len(hits) == 1, issues
    assert hits[0]["severity"] == "error"
    assert (hits[0]["union_a"], hits[0]["union_b"]) == ("a", "b")
    assert hits[0]["overlap_mm3"] == 100.0


def test_flush_contact_passes(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (10, 0, 0))  # x in [5, 15], shared face only
    assert (
        _hits(run_assembly_interference_check(_plan([{"id": "a"}, {"id": "b"}]), str(tmp_path)))
        == []
    )


def test_disjoint_passes(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (30, 0, 0))
    issues = run_assembly_interference_check(_plan([{"id": "a"}, {"id": "b"}]), str(tmp_path))
    assert [i for i in issues if i["severity"] == "error"] == []


def test_co_plated_overlap_left_to_plate_clearance(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (9, 0, 0))
    plan = _plan([{"id": "a", "plate": "p"}, {"id": "b", "plate": "p"}])
    assert _hits(run_assembly_interference_check(plan, str(tmp_path))) == []


def test_press_fit_joint_exempt(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (9, 0, 0))
    plan = _plan([{"id": "a"}, {"id": "b"}], [_joint(-0.1)])
    assert _hits(run_assembly_interference_check(plan, str(tmp_path))) == []


def test_gap_fit_joint_not_exempt(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (9, 0, 0))
    plan = _plan([{"id": "a"}, {"id": "b"}], [_joint(0.1)])
    assert len(_hits(run_assembly_interference_check(plan, str(tmp_path)))) == 1


def test_copy_of_member_part_inherits_exemption(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (30, 0, 0))
    box_stl(tmp_path / "b2.stl", (9, 0, 0))  # copy of b, overlaps a
    parts = [{"id": "a"}, {"id": "b"}, {"id": "b2", "copy_of": {"part": "b"}}]
    exempt = run_assembly_interference_check(_plan(parts, [_joint(-0.1)]), str(tmp_path))
    assert _hits(exempt) == []
    assert len(_hits(run_assembly_interference_check(_plan(parts), str(tmp_path)))) == 1


def test_multi_union_member_names_its_union(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b_body.stl", (9, 0, 0))  # overlaps a
    box_stl(tmp_path / "b_lid.stl", (-9, 0, 0))  # overlaps a too, not b_body
    parts = [
        {"id": "a"},
        {"id": "b", "unions": [{"id": "b_body"}, {"id": "b_lid"}]},
    ]
    joint = _joint(-0.1)
    joint["members"][1]["union"] = "b_body"
    hits = _hits(run_assembly_interference_check(_plan(parts, [joint]), str(tmp_path)))
    assert [(h["union_a"], h["union_b"]) for h in hits] == [("a", "b_lid")]


def test_missing_stl_is_check_skipped(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    issues = run_assembly_interference_check(_plan([{"id": "a"}, {"id": "b"}]), str(tmp_path))
    assert issues and all(i["type"] == "check_skipped" for i in issues)
    assert any("not found" in i["message"] for i in issues)
    assert all(i["severity"] == "warning" for i in issues)
