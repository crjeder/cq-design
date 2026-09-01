"""Tests for BUILD_PLAN.json validation."""

import json
import os
import sys
from typing import Any

import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

from plan_validate import check_block_thinness, validate_plan  # noqa: E402

VALID_PLAN: dict[str, Any] = {
    "schema_version": 1,
    "intent": "Arduino Nano enclosure",
    "printer": "Bambu P1S",
    "material": "PLA",
    "nozzle_mm": 0.4,
    "parts": [
        {
            "id": "body",
            "description": "Main enclosure body",
            "dimensions": {"w_mm": 50, "d_mm": 35, "h_mm": 20},
            "interfaces": [{"type": "port_cutout", "connector": "usb_c", "wall": "front"}],
            "blocks_needed": ["hollow_box", "port_cutout"],
        }
    ],
    "constraints": {
        "wall_min_mm": 1.2,
        "overhang_max_deg": 45,
        "dimension_tolerance_mm": 1.0,
    },
}

VALID_PLAN_TWO_PARTS: dict[str, Any] = {
    **VALID_PLAN,
    "parts": [
        VALID_PLAN["parts"][0],  # type: ignore[index]
        {
            "id": "lid",
            "description": "Snap-fit lid",
            "dimensions": {"w_mm": 50, "d_mm": 35, "h_mm": 3},
            "interfaces": [],
            "blocks_needed": ["fillet_box", "snap_hook_clip"],
        },
    ],
}


@pytest.fixture
def plan_file(tmp_path):
    def _write(plan):
        p = tmp_path / "BUILD_PLAN.json"
        p.write_text(json.dumps(plan))
        return str(p)

    return _write


def test_valid_single_part(plan_file):
    errors = validate_plan(plan_file(VALID_PLAN))
    assert errors == []


def test_valid_two_parts(plan_file):
    errors = validate_plan(plan_file(VALID_PLAN_TWO_PARTS))
    assert errors == []


def test_valid_load_hint(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["load"] = {"dir": [1, 0, 0]}
    errors = validate_plan(plan_file(plan))
    assert errors == []


def test_missing_load_hint_is_valid(plan_file):
    # VALID_PLAN omits `load`; absence must not be an error.
    errors = validate_plan(plan_file(VALID_PLAN))
    assert errors == []


def test_zero_load_direction_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["load"] = {"dir": [0, 0, 0]}
    errors = validate_plan(plan_file(plan))
    assert any("non-zero direction" in e for e in errors)


def test_plan_level_optimize_for(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["optimize_for"] = "visual_quality"
    assert validate_plan(plan_file(plan)) == []


def test_per_part_optimize_for_override(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN_TWO_PARTS))
    plan["optimize_for"] = "strength"
    plan["parts"][1]["optimize_for"] = "min_support"
    assert validate_plan(plan_file(plan)) == []


def test_missing_optimize_for_is_valid(plan_file):
    assert validate_plan(plan_file(VALID_PLAN)) == []


def test_valid_show_face(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["show_face"] = {"dir": [0, 0, 1]}
    assert validate_plan(plan_file(plan)) == []


def test_valid_pose_intent(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["pose_intent"] = "stands upright, outward face toward world -Y"
    assert validate_plan(plan_file(plan)) == []


def test_missing_pose_intent_and_placement_is_valid(plan_file):
    # VALID_PLAN omits both pose_intent and placement; absence must not be an error.
    errors = validate_plan(plan_file(VALID_PLAN))
    assert errors == []


def _set_optimize_for_speed(p):
    p["optimize_for"] = "speed"


def _set_zero_show_face(p):
    p["parts"][0]["show_face"] = {"dir": [0, 0, 0]}


def _del_dimensions(p):
    del p["parts"][0]["dimensions"]


def _del_material(p):
    del p["material"]


def _set_unknown_block(p):
    p["parts"][0]["blocks_needed"] = ["nonexistent_block_xyz"]


@pytest.mark.parametrize(
    "mutate, expected_substring",
    [
        (_set_optimize_for_speed, "optimize_for"),
        (_set_zero_show_face, "non-zero direction"),
        (_del_dimensions, "dimensions"),
        (_del_material, "material"),
        (_set_unknown_block, "nonexistent_block_xyz"),
    ],
    ids=[
        "invalid_optimize_for",
        "zero_show_face_direction",
        "missing_dimensions",
        "missing_required_top_level",
        "unknown_block_name",
    ],
)
def test_invalid_plan_field_rejected(plan_file, mutate, expected_substring):
    plan = json.loads(json.dumps(VALID_PLAN))
    mutate(plan)
    errors = validate_plan(plan_file(plan))
    assert any(expected_substring in e for e in errors)


def test_empty_parts_array(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"] = []
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_two_parts_no_assembly_field(plan_file):
    """A multi-part plan validates with no `assembly` field; assembly is declarative."""
    errors = validate_plan(plan_file(VALID_PLAN_TWO_PARTS))
    assert errors == []


def test_assembly_field_rejected(plan_file):
    """A supplied `assembly` object is rejected by the schema (additionalProperties)."""
    plan = json.loads(json.dumps(VALID_PLAN_TWO_PARTS))
    plan["assembly"] = {"strategy": "snap_fit", "clearance_mm": 0.3}
    errors = validate_plan(plan_file(plan))
    assert any("assembly" in e for e in errors)


def test_interface_type_only_still_validates(plan_file):
    """An interface entry with only `type` (no structured placement) is valid."""
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["interfaces"] = [{"type": "port_cutout"}]
    errors = validate_plan(plan_file(plan))
    assert errors == []


def test_interface_structured_placement_validates(plan_file):
    """Structured position/size on an interface entry is accepted."""
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["interfaces"] = [
        {
            "type": "port_cutout",
            "wall": "south",
            "position_mm": [10.0, 0.0, 15.0],
            "size_mm": [9.0, 3.5],
        },
        {"type": "screw_boss", "position_mm": [5, 5, 0], "diameter_mm": 3.2},
    ]
    errors = validate_plan(plan_file(plan))
    assert errors == []


def test_interface_malformed_position_rejected(plan_file):
    """A `position_mm` that is not three numbers is rejected by the schema."""
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["interfaces"] = [{"type": "port_cutout", "position_mm": [10.0, 0.0]}]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_interface_unknown_field_rejected(plan_file):
    """An undefined interface field is rejected now that the entry is closed."""
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["interfaces"] = [{"type": "port_cutout", "bogus_field": 1}]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json")
    errors = validate_plan(str(p))
    assert len(errors) >= 1


def test_nonexistent_file():
    errors = validate_plan("/no/such/file/BUILD_PLAN.json")
    assert len(errors) >= 1


def test_block_object_form_validates(plan_file):
    """blocks_needed items may be objects carrying name + extents_mm."""
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["blocks_needed"] = [
        {"name": "hollow_box", "extents_mm": [50, 35, 20]},
        "port_cutout",
    ]
    assert validate_plan(plan_file(plan)) == []


def test_thin_block_flagged_with_attribution():
    """A block whose smallest extent is below wall_min is flagged by part,
    block, and axis."""
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["blocks_needed"] = [{"name": "fillet_box", "extents_mm": [0.8, 35, 20]}]
    findings = check_block_thinness(plan)
    assert len(findings) == 1
    assert "body" in findings[0]
    assert "fillet_box" in findings[0]
    assert "x-extent" in findings[0]


def test_thick_blocks_no_findings():
    """Blocks at or above wall_min, or without declared extents, are not flagged."""
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["blocks_needed"] = [
        {"name": "hollow_box", "extents_mm": [50, 35, 20]},
        "port_cutout",
    ]
    assert check_block_thinness(plan) == []


# ---- multi-union parts: union namespace ----


def test_part_with_unions_validates(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["unions"] = [{"id": "u_a"}, {"id": "u_b", "plate": "p2"}]
    assert validate_plan(plan_file(plan)) == []


def test_duplicate_union_ids_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["unions"] = [{"id": "dup"}, {"id": "dup"}]
    errors = validate_plan(plan_file(plan))
    assert any("declared more than once" in e for e in errors)


def test_union_id_colliding_with_part_id_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["unions"] = [{"id": "shared_name"}]
    plan["parts"].append(
        {
            "id": "shared_name",
            "description": "Another part whose id collides with a sub-union id",
            "dimensions": {"w_mm": 10, "d_mm": 10, "h_mm": 10},
            "interfaces": [],
            "blocks_needed": [],
        }
    )
    errors = validate_plan(plan_file(plan))
    assert any("declared more than once" in e for e in errors)


def test_keep_out_reserved_as_sub_union_id_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["unions"] = [{"id": "keep_out"}]
    errors = validate_plan(plan_file(plan))
    assert any("reserved" in e and "keep_out" in e for e in errors)


def test_named_interface_validates(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["interfaces"][0]["name"] = "inner_lip"
    assert validate_plan(plan_file(plan)) == []


@pytest.mark.parametrize("bad_name", ["Inner Lip", "inner-lip"])
def test_non_normalized_interface_name_rejected(plan_file, bad_name):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["interfaces"][0]["name"] = bad_name
    errors = validate_plan(plan_file(plan))
    assert any("name" in e for e in errors)


def test_duplicate_interface_name_within_part_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["interfaces"] = [
        {"type": "screw_mount", "name": "mount_hole"},
        {"type": "screw_mount", "name": "mount_hole"},
    ]
    errors = validate_plan(plan_file(plan))
    assert any("interface name 'mount_hole' is declared more than once" in e for e in errors)


def test_same_interface_name_on_different_parts_accepted(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN_TWO_PARTS))
    plan["parts"][0]["interfaces"] = [{"type": "screw_mount", "name": "mount_hole"}]
    plan["parts"][1]["interfaces"] = [{"type": "screw_mount", "name": "mount_hole"}]
    assert validate_plan(plan_file(plan)) == []


def test_unnamed_interfaces_do_not_collide(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["interfaces"] = [
        {"type": "screw_mount"},
        {"type": "screw_mount"},
        {"type": "screw_mount"},
    ]
    assert validate_plan(plan_file(plan)) == []


def test_keep_out_reserved_as_part_id_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["id"] = "keep_out"
    errors = validate_plan(plan_file(plan))
    assert any("reserved" in e and "keep_out" in e for e in errors)


def _plan_with_pin_hinge_kinematics(placement=None):
    plan = json.loads(json.dumps(VALID_PLAN))
    if placement is not None:
        plan["parts"][0]["placement"] = placement
    plan["kinematics"] = [
        {
            "joint_id": "j1",
            "moving_union": "body",
            "block": "pin_hinge",
            "axis_origin_mm": [0, 0, 0],
            "axis_dir": "Y",
            "type": "revolute",
            "required_range": [0, 90],
            "step": 5,
        }
    ]
    return plan


def test_kinematics_no_placement_defers_axis_arm(plan_file):
    """A moving union whose part has no placement yet: no joint_contract error,
    and the deferred axis arm shows up as a non-fatal advisory."""
    from plan_validate import check_deferred_axis_arms

    plan = _plan_with_pin_hinge_kinematics(placement=None)
    errors = validate_plan(plan_file(plan))
    assert not any("joint axis_dir" in e or "not coaxial" in e for e in errors)

    findings = check_deferred_axis_arms(plan)
    assert len(findings) == 1
    assert "j1" in findings[0]
    assert "deferred" in findings[0]


def test_kinematics_placement_rotating_axis_off_still_errors(plan_file):
    """With a placement in place, a block axis rotated away from axis_dir still
    produces the joint_contract error (D5: authoritative once placement exists)."""
    plan = _plan_with_pin_hinge_kinematics(placement={"rotate": [{"axis": "Z", "angle_deg": 90}]})
    errors = validate_plan(plan_file(plan))
    assert any("joint axis_dir" in e for e in errors)

    from plan_validate import check_deferred_axis_arms

    assert check_deferred_axis_arms(plan) == []


def test_moving_union_may_reference_a_sub_union(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["unions"] = [{"id": "leaf_a"}, {"id": "leaf_b"}]
    plan["kinematics"] = [
        {
            "joint_id": "j1",
            "moving_union": "leaf_a",
            "block": "pin_hinge",
            "axis_origin_mm": [0, 0, 0],
            "axis_dir": "Y",
            "type": "revolute",
            "required_range": [0, 90],
            "step": 5,
        }
    ]
    errors = validate_plan(plan_file(plan))
    assert not any("is not a union id" in e for e in errors)


def _plan_with_joint(**entry_over):
    """VALID_PLAN with one sub-union `mover` and a single kinematics joint to override."""
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["unions"] = [{"id": "mover"}]
    entry = {
        "joint_id": "j1",
        "moving_union": "mover",
        "block": "pin_hinge",  # revolute, dof axis +Y through origin
        "axis_origin_mm": [0, 0, 0],
        "axis_dir": "Y",
        "type": "revolute",
        "required_range": [0, 90],
        "step": 5,
    }
    entry.update(entry_over)
    plan["kinematics"] = [entry]
    return plan


def test_contract_type_mismatch_rejected(plan_file):
    # revolute wish against a spherical block (ball_socket) violates the type arm.
    plan = _plan_with_joint(block="ball_socket", type="revolute")
    errors = validate_plan(plan_file(plan))
    assert any("does not match" in e and "spherical" in e for e in errors)


def test_contract_revolute_wrong_axis_rejected(plan_file):
    # pin_hinge's dof axis is +Y; a Z wish is not parallel. The axis arm is only
    # authoritative once the part carries a placement (identity here, so the block
    # axis is unrotated); see test_kinematics_no_placement_defers_axis_arm.
    plan = _plan_with_joint(axis_dir="Z")
    plan["parts"][0]["placement"] = {"rotate": [{"axis": "Y", "angle_deg": 0}]}
    errors = validate_plan(plan_file(plan))
    assert any("not parallel" in e for e in errors)


def test_contract_revolute_parallel_but_off_line_rejected(plan_file):
    # Axis parallel (+Y) but the pivot is off the block's axis line -> not coaxial.
    plan = _plan_with_joint(axis_dir="Y", axis_origin_mm=[5, 0, 0])
    plan["parts"][0]["placement"] = {"rotate": [{"axis": "Y", "angle_deg": 0}]}
    errors = validate_plan(plan_file(plan))
    assert any("not coaxial" in e for e in errors)


def test_contract_prismatic_parallel_offset_passes(plan_file):
    # Prismatic only needs parallel direction; an offset axis position is fine.
    plan = _plan_with_joint(
        block="dovetail_groove", type="prismatic", axis_dir="Y", axis_origin_mm=[5, 0, 0]
    )
    errors = validate_plan(plan_file(plan))
    assert not any("Kinematics 'j1'" in e for e in errors)


def test_contract_matching_revolute_passes(plan_file):
    plan = _plan_with_joint()  # pin_hinge, revolute, +Y axis through origin
    errors = validate_plan(plan_file(plan))
    assert not any("Kinematics 'j1'" in e for e in errors)


def test_contract_spherical_joint_is_skipped(plan_file):
    # Spherical is parked: no joint_contract finding even with a non-matching axis.
    plan = _plan_with_joint(block="ball_socket", type="spherical", axis_dir="Z")
    errors = validate_plan(plan_file(plan))
    assert not any("Kinematics 'j1'" in e for e in errors)


# ---- nested `children` (recursive kinematics tree) ---------------------------


def _joint_entry(joint_id, moving_union, **extra):
    entry = {
        "joint_id": joint_id,
        "moving_union": moving_union,
        "block": "pin_hinge",
        "axis_origin_mm": [0, 0, 0],
        "axis_dir": "Y",
        "type": "revolute",
        "required_range": [0, 90],
        "step": 5,
    }
    entry.update(extra)
    return entry


def test_nested_child_entry_is_validated(plan_file):
    # A validation failure in a nested `children` entry is still reported.
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["unions"] = [{"id": "shoulder"}, {"id": "forearm"}]
    forearm = _joint_entry("elbow", "forearm", block="no_such_block")
    shoulder = _joint_entry("shoulder_joint", "shoulder", children=[forearm])
    plan["kinematics"] = [shoulder]
    errors = validate_plan(plan_file(plan))
    assert any("unknown block 'no_such_block'" in e for e in errors)


def test_three_level_nested_chain_failure_is_reported(plan_file):
    # A validation failure three levels deep under `children` is still reported.
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["unions"] = [{"id": "shoulder"}, {"id": "forearm"}, {"id": "hand"}]
    hand = _joint_entry("wrist", "hand", block="no_such_block")
    forearm = _joint_entry("elbow", "forearm", children=[hand])
    shoulder = _joint_entry("shoulder_joint", "shoulder", children=[forearm])
    plan["kinematics"] = [shoulder]
    errors = validate_plan(plan_file(plan))
    assert any("unknown block 'no_such_block'" in e for e in errors)


def test_three_level_nested_chain_passes(plan_file):
    # A deeply nested valid chain (shoulder -> forearm -> hand) passes.
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["unions"] = [{"id": "shoulder"}, {"id": "forearm"}, {"id": "hand"}]
    hand = _joint_entry("wrist", "hand")
    forearm = _joint_entry("elbow", "forearm", children=[hand])
    shoulder = _joint_entry("shoulder_joint", "shoulder", children=[forearm])
    plan["kinematics"] = [shoulder]
    errors = validate_plan(plan_file(plan))
    assert errors == []


def test_top_level_entry_with_no_children_is_unaffected(plan_file):
    # Regression: an entry with no `children` behaves exactly as before this field existed.
    plan = _plan_with_joint()
    errors = validate_plan(plan_file(plan))
    assert errors == []


# ---- blockless-kinematics (directly-declared, no inventory block) ------------


def test_blockless_entry_validates_with_no_contract_error(plan_file):
    # No `block`: contract arms (type/axis/coaxiality) are out of scope by construction.
    plan = _plan_with_joint()
    del plan["kinematics"][0]["block"]
    errors = validate_plan(plan_file(plan))
    assert not any("Kinematics 'j1'" in e for e in errors)


def test_blockless_entry_with_bad_moving_union_still_fails(plan_file):
    # The union-id check is unconditional even without a block.
    plan = _plan_with_joint(moving_union="no_such_union")
    del plan["kinematics"][0]["block"]
    errors = validate_plan(plan_file(plan))
    assert any("is not a union id" in e for e in errors)


def test_blockbacked_entry_contract_checks_still_apply(plan_file):
    # Regression: a block-backed entry keeps the full contract (unaffected by the
    # block-less branch added alongside it), once the part carries a placement.
    plan = _plan_with_joint(axis_dir="Z")  # pin_hinge's dof axis is +Y; Z is not parallel
    plan["parts"][0]["placement"] = {"rotate": [{"axis": "Y", "angle_deg": 0}]}
    errors = validate_plan(plan_file(plan))
    assert any("not parallel" in e for e in errors)


# ---- joint-mate-entity (cross-part matched-pair joints) -----------------------


def _part(pid, **extra):
    part = {
        "id": pid,
        "description": f"part {pid}",
        "dimensions": {"w_mm": 50, "d_mm": 5, "h_mm": 80},
        "interfaces": [],
        "blocks_needed": [],
    }
    part.update(extra)
    return part


def _joints_plan(joint_over=None, root_part: str | None = "door", door_over=None, wall_over=None):
    """Two-part plan (door, wall) wired by one pin_hinge joints entry."""
    plan = json.loads(json.dumps(VALID_PLAN))
    door = _part("door", **(door_over or {}))
    wall = _part("wall", **(wall_over or {}))
    plan["parts"] = [door, wall]
    joint = {
        "joint_id": "hinge1",
        "block": "pin_hinge",
        "params": {},
        "members": [
            {"member": "leaf_a", "part": "door"},
            {"member": "leaf_b", "part": "wall"},
        ],
    }
    if joint_over:
        joint.update(joint_over)
    plan["joints"] = [joint]
    if root_part is not None:
        plan["root_part"] = root_part
    return plan


def test_joint_valid_two_part_plan_passes(plan_file):
    errors = validate_plan(plan_file(_joints_plan()))
    assert errors == []


def test_joint_dovetail_corner_block_validates_and_derives_pose(plan_file):
    """dovetail_corner_joint backs a cross-part joints entry (pins/tails on two boards)."""
    plan = _joints_plan(
        joint_over={
            "block": "dovetail_corner_joint",
            "members": [
                {"member": "pins", "part": "door"},
                {"member": "tails", "part": "wall", "dock": {"translate_mm": [0, 0, 10]}},
            ],
        }
    )
    assert validate_plan(plan_file(plan)) == []

    from mate_chain import compute_mate_poses
    from placement import to_matrix

    poses = compute_mate_poses(plan)
    assert set(poses) == {"wall"}
    import numpy as np

    np.testing.assert_allclose(poses["wall"], to_matrix({"translate_mm": [0, 0, -10]}), atol=1e-9)


def test_joint_unknown_block_rejected(plan_file):
    plan = _joints_plan(joint_over={"block": "no_such_block"})
    errors = validate_plan(plan_file(plan))
    assert any("unknown block 'no_such_block'" in e for e in errors)


def test_joint_block_without_emits_rejected(plan_file):
    plan = _joints_plan(joint_over={"block": "hollow_box"})
    errors = validate_plan(plan_file(plan))
    assert any("has no 'emits' descriptor" in e for e in errors)


def test_joint_unknown_member_id_rejected(plan_file):
    plan = _joints_plan()
    plan["joints"][0]["members"][0]["member"] = "leaf_c"
    errors = validate_plan(plan_file(plan))
    assert any("'leaf_c' is not one of block" in e for e in errors)


def test_joint_duplicate_member_id_rejected(plan_file):
    plan = _joints_plan()
    plan["joints"][0]["members"][1]["member"] = "leaf_a"
    errors = validate_plan(plan_file(plan))
    assert any("must reference distinct emits ids" in e for e in errors)


def test_joint_unknown_part_rejected(plan_file):
    plan = _joints_plan()
    plan["joints"][0]["members"][1]["part"] = "ghost"
    errors = validate_plan(plan_file(plan))
    assert any("part 'ghost' is not a declared part id" in e for e in errors)


def test_joint_same_part_for_both_members_rejected(plan_file):
    plan = _joints_plan()
    plan["joints"][0]["members"][1]["part"] = "door"
    errors = validate_plan(plan_file(plan))
    assert any("both members reference the same part 'door'" in e for e in errors)


def test_joint_missing_root_part_rejected_by_schema(plan_file):
    plan = _joints_plan(root_part=None)
    errors = validate_plan(plan_file(plan))
    assert any("root_part" in e for e in errors)


def test_joint_unanchored_part_rejected(plan_file):
    plan = _joints_plan()
    plan["parts"].append(_part("orphan_a"))
    plan["parts"].append(_part("orphan_b"))
    plan["joints"].append(
        {
            "joint_id": "hinge2",
            "block": "pin_hinge",
            "params": {},
            "members": [
                {"member": "leaf_a", "part": "orphan_a"},
                {"member": "leaf_b", "part": "orphan_b"},
            ],
        }
    )
    errors = validate_plan(plan_file(plan))
    assert any("orphan_a' is unanchored" in e for e in errors)
    assert any("orphan_b' is unanchored" in e for e in errors)


def test_joint_cycle_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"] = [_part("a"), _part("b"), _part("c")]
    plan["root_part"] = "a"

    def _hinge(jid, part_x, part_y):
        return {
            "joint_id": jid,
            "block": "pin_hinge",
            "params": {},
            "members": [
                {"member": "leaf_a", "part": part_x},
                {"member": "leaf_b", "part": part_y},
            ],
        }

    plan["joints"] = [_hinge("ab", "a", "b"), _hinge("bc", "b", "c"), _hinge("ca", "c", "a")]
    errors = validate_plan(plan_file(plan))
    assert any("conflicting mate path" in e for e in errors)


def test_joint_double_anchored_part_rejected(plan_file):
    plan = _joints_plan(wall_over={"placement": {"translate_mm": [0, 0, 10]}})
    errors = validate_plan(plan_file(plan))
    assert any("wall' is double-anchored" in e for e in errors)


def test_root_part_own_placement_is_not_double_anchored(plan_file):
    plan = _joints_plan(door_over={"placement": {"translate_mm": [1, 2, 3]}})
    errors = validate_plan(plan_file(plan))
    assert errors == []


def test_plan_without_joints_needs_no_root_part(plan_file):
    # Regression: no `joints` array means no `root_part` requirement and every
    # part keeps using its own placement mechanism unchanged.
    errors = validate_plan(plan_file(VALID_PLAN))
    assert errors == []


# ---- request_log ---------------------------------------------------------


def test_plan_without_request_log_is_valid(plan_file):
    # Regression: existing plans (including eval-corpus goldens) have no
    # request_log at all; absence must not be an error.
    errors = validate_plan(plan_file(VALID_PLAN))
    assert errors == []


def test_well_formed_request_log_validates(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "Make an enclosure"},
        {"ts": "2026-07-19T10:05:00Z", "kind": "clarification", "text": "USB-C on the south wall"},
        {"ts": "2026-07-19T11:00:00Z", "kind": "correction", "text": "Actually make it 5mm taller"},
    ]
    assert validate_plan(plan_file(plan)) == []


def test_request_log_entry_with_images_validates(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "Make an enclosure"},
        {
            "ts": "2026-07-19T11:00:00Z",
            "kind": "correction",
            "text": "Ear should sit lower, see sketch",
            "images": ["sketches/ear-placement-2026-07-19T11-00-00Z.png"],
        },
    ]
    assert validate_plan(plan_file(plan)) == []


def test_request_log_empty_images_array_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "hi", "images": []}
    ]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_request_log_empty_image_path_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "hi", "images": [""]}
    ]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_request_log_unknown_kind_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [{"ts": "2026-07-19T10:00:00Z", "kind": "bogus", "text": "hi"}]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_request_log_empty_text_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [{"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": ""}]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_request_log_extra_property_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "hi", "extra": 1}
    ]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_request_log_missing_field_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [{"ts": "2026-07-19T10:00:00Z", "kind": "initial"}]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_request_log_zero_initial_entries_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [{"ts": "2026-07-19T10:00:00Z", "kind": "clarification", "text": "hi"}]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_request_log_duplicate_initial_entries_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "hi"},
        {"ts": "2026-07-19T10:05:00Z", "kind": "initial", "text": "again"},
    ]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_request_log_non_first_initial_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "clarification", "text": "hi"},
        {"ts": "2026-07-19T10:05:00Z", "kind": "initial", "text": "again"},
    ]
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_request_log_level_and_targets_validate(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "Make a cradle"},
        {
            "ts": "2026-07-19T11:00:00Z",
            "kind": "correction",
            "text": "saddle should be 40mm wide",
            "level": "parameter",
            "targets": ["cradle", "cradle.saddle_width"],
        },
    ]
    assert validate_plan(plan_file(plan)) == []


def test_request_log_mixed_typed_and_untyped_entries_validate(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "Make a cradle"},
        {"ts": "2026-07-19T10:30:00Z", "kind": "clarification", "text": "press fit"},
        {
            "ts": "2026-07-19T11:00:00Z",
            "kind": "correction",
            "text": "add a drain slot",
            "level": "operation",
            "targets": ["base"],
        },
    ]
    assert validate_plan(plan_file(plan)) == []


def test_request_log_unknown_level_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "hi", "level": "bogus"}
    ]
    assert len(validate_plan(plan_file(plan))) >= 1


def test_request_log_empty_targets_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "hi", "targets": []}
    ]
    assert len(validate_plan(plan_file(plan))) >= 1


def test_request_log_empty_target_string_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "hi", "targets": [""]}
    ]
    assert len(validate_plan(plan_file(plan))) >= 1


def test_request_log_non_array_targets_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "hi", "targets": "cradle"}
    ]
    assert len(validate_plan(plan_file(plan))) >= 1


# ---- review_policy --------------------------------------------------------


def test_plan_level_review_policy(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["review_policy"] = "minimal"
    assert validate_plan(plan_file(plan)) == []


def test_missing_review_policy_is_valid(plan_file):
    # VALID_PLAN omits `review_policy`; absence must not be an error (defaults
    # to every_stage downstream).
    assert validate_plan(plan_file(VALID_PLAN)) == []


def test_invalid_review_policy_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["review_policy"] = "sometimes"
    errors = validate_plan(plan_file(plan))
    assert any("review_policy" in e for e in errors)


def test_valid_archetype_passes(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["archetype"] = "enclosure-body"
    assert validate_plan(plan_file(plan)) == []


def test_unknown_archetype_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["archetype"] = "no-such-shape"
    errors = validate_plan(plan_file(plan))
    assert any("no-such-shape" in e and "body" in e for e in errors)


def test_plan_without_archetypes_stays_valid(plan_file):
    # VALID_PLAN carries no `archetype` field on any part.
    assert validate_plan(plan_file(VALID_PLAN)) == []
