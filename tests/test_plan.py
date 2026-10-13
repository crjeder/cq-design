"""Tests for src/plan.py -- BUILD_PLAN.json validate / summary / import-params.

Fast tier, no CadQuery.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

from plan import (  # noqa: E402
    _INVENTORY_PATH,
    check_block_thinness,
    check_bom_coverage,
    check_coordinate_frame_usage,
    check_engineering_rationale,
    check_hinge_intent_without_joints,
    check_load_case_anchors,
    check_shared_interfaces,
    parse_parameters,
    reconcile,
    run,
    summarize,
    validate_plan,
)

VALID_PLAN: dict[str, Any] = {
    "schema_version": 1,
    "intent": (
        "Open-top enclosure for an Arduino Nano, printed as a single body with 1.2 mm "
        "walls and a USB-C pass-through on the front wall. Board seats on internal "
        "standoffs (press fit, assumed 0.2 mm clearance -- adjust after a test fit)."
    ),
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


def test_token_intent_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["intent"] = "A laptop stand"
    errors = validate_plan(plan_file(plan))
    assert any("intent" in e for e in errors)


def test_reformulation_length_intent_passes(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["intent"] = (
        "A wedge phone stand printed as one part, back face raked 65 degrees from "
        "horizontal (assumed -- adjust after a test fit), sized for a phone in landscape."
    )
    assert validate_plan(plan_file(plan)) == []


def test_negative_one_dimension_still_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["dimensions"]["d_mm"] = -1
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_negative_one_in_signed_fields_still_validates(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["load"] = {"dir": [0, 0, -1]}
    plan["parts"][0]["interfaces"] = [
        {"type": "screw_boss", "position_mm": [-12.5, 0, 4], "diameter_mm": 3.2}
    ]
    assert validate_plan(plan_file(plan)) == []


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


def test_valid_load_case_accepted(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["interfaces"] = [
        {"type": "screw_boss", "name": "wall_screws", "position_mm": [0, 0, 0], "diameter_mm": 3},
        {"type": "shelf", "name": "phone_shelf", "position_mm": [10, 0, 0], "size_mm": [5, 5]},
    ]
    plan["parts"][0]["load"] = {
        "dir": [0, 0, -1],
        "type": "bending",
        "magnitude_n": 2.6,
        "applied_at": "phone_shelf",
        "applied_dir": [0, -0.5, -1],
        "grounded_at": ["wall_screws"],
    }
    errors = validate_plan(plan_file(plan))
    assert errors == []


def test_partial_load_case_accepted(plan_file):
    # magnitude_n/applied_at/applied_dir/grounded_at are all independently optional.
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["load"] = {"dir": [0, 0, -1], "magnitude_n": 1.5}
    errors = validate_plan(plan_file(plan))
    assert errors == []


def test_dir_only_load_unchanged(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["load"] = {"dir": [0, 0, -1], "type": "bending"}
    errors = validate_plan(plan_file(plan))
    assert errors == []


def test_load_anchor_naming_missing_interface_reported(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["load"] = {"dir": [0, 0, -1], "applied_at": "does_not_exist"}
    plan_path = plan_file(plan)
    assert validate_plan(plan_path) == []  # not a schema error
    findings = check_load_case_anchors(plan)
    assert any("does_not_exist" in f for f in findings)


def test_load_anchor_grounded_at_missing_interface_reported():
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["load"] = {"dir": [0, 0, -1], "grounded_at": ["nope"]}
    findings = check_load_case_anchors(plan)
    assert any("nope" in f for f in findings)


def test_load_anchor_matching_interface_no_findings():
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["interfaces"] = [
        {"type": "screw_boss", "name": "wall_screws", "position_mm": [0, 0, 0], "diameter_mm": 3}
    ]
    plan["parts"][0]["load"] = {"dir": [0, 0, -1], "grounded_at": ["wall_screws"]}
    assert check_load_case_anchors(plan) == []


def test_load_anchor_check_no_load_no_findings():
    assert check_load_case_anchors(VALID_PLAN) == []


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


# ---- engineering_rationale schema + trigger check ----


def test_rationale_object_form_validates(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["load"] = {"dir": [0, 0, -1]}
    plan["parts"][0]["engineering_rationale"] = {
        "load_path": "base bears the enclosed board weight",
        "worst_case_stress": "floor, center span",
        "check": "deflection = 5*w*L^4/(384*E*I) = 0.02 mm <= 0.1 mm allowable (PLA)",
    }
    assert validate_plan(plan_file(plan)) == []


def test_rationale_string_form_validates(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["engineering_rationale"] = "no load-bearing features (static cosmetic part)"
    assert validate_plan(plan_file(plan)) == []


def test_rationale_string_form_without_reason_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["engineering_rationale"] = "no load-bearing features"
    errors = validate_plan(plan_file(plan))
    assert any("engineering_rationale" in e for e in errors)


def test_rationale_object_missing_check_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["engineering_rationale"] = {
        "load_path": "x",
        "worst_case_stress": "y",
    }
    errors = validate_plan(plan_file(plan))
    assert any("engineering_rationale" in e for e in errors)


def test_rationale_missing_field_is_advisory_finding():
    plan = json.loads(json.dumps(VALID_PLAN))
    findings = check_engineering_rationale(plan)
    assert len(findings) == 1
    assert "body" in findings[0]


def test_rationale_load_bearing_part_needs_object_form():
    """A part declaring `load` but carrying the string form is flagged."""
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["load"] = {"dir": [0, 0, -1]}
    plan["parts"][0]["engineering_rationale"] = "no load-bearing features (flat plate)"
    findings = check_engineering_rationale(plan)
    assert len(findings) == 1
    assert "body" in findings[0]


def test_rationale_load_bearing_block_without_declared_load_still_triggers():
    """blocks_needed alone (no `load` field) is enough to require the object form."""
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["blocks_needed"] = ["hollow_box", "screw_boss"]
    plan["parts"][0]["engineering_rationale"] = "no load-bearing features (n/a)"
    findings = check_engineering_rationale(plan)
    assert len(findings) == 1


def test_rationale_string_form_on_untriggered_part_passes():
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["engineering_rationale"] = "no load-bearing features (static cosmetic part)"
    assert check_engineering_rationale(plan) == []


def test_rationale_object_form_on_triggered_part_passes():
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["load"] = {"dir": [0, 0, -1]}
    plan["parts"][0]["engineering_rationale"] = {
        "load_path": "base bears the enclosed board weight",
        "worst_case_stress": "floor, center span",
        "check": "deflection = 0.02 mm <= 0.1 mm allowable (PLA)",
    }
    assert check_engineering_rationale(plan) == []


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
    from plan import check_deferred_axis_arms

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

    from plan import check_deferred_axis_arms

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


def _ring_plan(n=4, off_mm=0.0, block="dovetail_corner_joint", members=("pins", "tails")):
    """n parts in a ring; each joint docks +10 mm along X and the ring's last joint
    returns -(n-1)*10 so the docks compose to identity (off_mm perturbs it)."""
    plan = json.loads(json.dumps(VALID_PLAN))
    ids = [f"p{i}" for i in range(n)]
    plan["parts"] = [_part(i) for i in ids]
    plan["root_part"] = ids[0]
    plan["joints"] = []
    for k in range(n):
        x = 10.0 if k < n - 1 else -(n - 1) * 10.0 + off_mm
        plan["joints"].append(
            {
                "joint_id": f"j{k}",
                "block": block,
                "params": {},
                "members": [
                    {"member": members[0], "part": ids[k], "dock": {"translate_mm": [x, 0, 0]}},
                    {"member": members[1], "part": ids[(k + 1) % n]},
                ],
            }
        )
    return plan


def test_joint_rigid_loop_accepted(plan_file):
    assert validate_plan(plan_file(_ring_plan())) == []


def test_joint_rigid_loop_poses_match_spanning_tree(plan_file):
    import numpy as np

    from mate_chain import compute_mate_poses

    plan = _ring_plan()
    poses = compute_mate_poses(plan)
    assert set(poses) == {"p1", "p2", "p3"}
    assert np.allclose(poses["p3"][:3, 3], [30, 0, 0])


def test_joint_rigid_loop_residual_rejected(plan_file):
    errors = validate_plan(plan_file(_ring_plan(off_mm=2.0)))
    assert any("does not close the loop" in e and "2.000 mm" in e for e in errors)


def test_joint_duplicate_pair_checked(plan_file):
    plan = _joints_plan(
        joint_over={
            "block": "dovetail_corner_joint",
            "members": [{"member": "pins", "part": "door"}, {"member": "tails", "part": "wall"}],
        }
    )
    dup = json.loads(json.dumps(plan["joints"][0]))
    dup["joint_id"] = "dup"
    plan["joints"].append(dup)
    assert validate_plan(plan_file(plan)) == []
    plan["joints"][1]["members"][0]["dock"] = {"translate_mm": [0, 0, 3]}
    errors = validate_plan(plan_file(plan))
    assert any("'dup' does not close the loop" in e for e in errors)


def test_joint_mixed_rigid_and_hinge_loop_rejected(plan_file):
    plan = _ring_plan()
    plan["joints"][1].update(
        block="pin_hinge",
        members=[
            {"member": "leaf_a", "part": "p1"},
            {"member": "leaf_b", "part": "p2"},
        ],
    )
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
    plan["intent_ts"] = "2026-07-19T11:00:00Z"
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
    plan["intent_ts"] = max(e["ts"] for e in plan["request_log"])
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
    plan["intent_ts"] = max(e["ts"] for e in plan["request_log"])
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
    plan["intent_ts"] = max(e["ts"] for e in plan["request_log"])
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


def test_request_log_script_baseline_validates(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "Make a cradle"},
        {
            "ts": "2026-07-19T11:00:00Z",
            "kind": "correction",
            "text": "saddle should be 40mm wide",
            "level": "parameter",
            "targets": ["cradle"],
            "script_baseline": {"cradle": "9f86d0", "plate": "3b5d5c"},
        },
    ]
    plan["intent_ts"] = max(e["ts"] for e in plan["request_log"])
    assert validate_plan(plan_file(plan)) == []


@pytest.mark.parametrize("bad", [["cradle"], {"cradle": 1}, {"cradle": ""}])
def test_request_log_bad_script_baseline_rejected(plan_file, bad):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "hi", "script_baseline": bad}
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


# ---- shared interface names without a joints entry ----------------------------


def _bore(pid_plan, pid):
    """Give part `pid` a named pivot_bore interface."""
    for part in pid_plan["parts"]:
        if part["id"] == pid:
            part["interfaces"] = [{"type": "pin_bore", "name": "pivot_bore"}]
    return pid_plan


def test_shared_interface_name_without_joint_flagged():
    """The C5 case: one bore named on two parts nothing links."""
    plan = _joints_plan()
    del plan["joints"]
    del plan["root_part"]
    _bore(plan, "door")
    _bore(plan, "wall")
    findings = check_shared_interfaces(plan)
    assert len(findings) == 1
    assert "pivot_bore" in findings[0]
    assert "door" in findings[0] and "wall" in findings[0]


def test_shared_interface_name_with_joint_not_flagged():
    plan = _joints_plan()
    _bore(plan, "door")
    _bore(plan, "wall")
    assert check_shared_interfaces(plan) == []


def test_single_part_and_unnamed_interfaces_not_flagged():
    plan = _joints_plan()
    del plan["joints"]
    del plan["root_part"]
    _bore(plan, "door")
    plan["parts"][1]["interfaces"] = [{"type": "pin_bore"}]
    assert check_shared_interfaces(plan) == []


def test_third_holder_flagged_when_pair_is_linked():
    plan = _joints_plan()
    plan["parts"].append(_part("strut"))
    for pid in ("door", "wall", "strut"):
        _bore(plan, pid)
    findings = check_shared_interfaces(plan)
    assert len(findings) == 1
    assert "strut" in findings[0]
    assert "door" not in findings[0] and "wall" not in findings[0]


def test_shared_interface_finding_does_not_invalidate_plan(plan_file):
    """Advisory only -- it must not reach the gate's plan_invalid path."""
    plan = _joints_plan()
    del plan["joints"]
    del plan["root_part"]
    _bore(plan, "door")
    _bore(plan, "wall")
    assert check_shared_interfaces(plan)
    assert validate_plan(plan_file(plan)) == []


# ---- coordinate_frame (schema + advisory) --------------------------------------


def test_coordinate_frame_absent_validates(plan_file):
    assert validate_plan(plan_file(VALID_PLAN)) == []


def test_valid_coordinate_frame_validates(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["coordinate_frame"] = {"east": "-x", "north": "+y", "up": "+z"}
    assert validate_plan(plan_file(plan)) == []


def test_invalid_coordinate_frame_axis_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["coordinate_frame"] = {"east": "sideways"}
    errors = validate_plan(plan_file(plan))
    assert any("coordinate_frame" in e for e in errors)


def test_compass_word_in_intent_flags():
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["intent"] = plan["intent"] + " Fillet added on the east side of the enclosure."
    findings = check_coordinate_frame_usage(plan)
    assert len(findings) == 1


def test_compass_word_in_request_log_flags():
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "Mount it on the West wall"}
    ]
    findings = check_coordinate_frame_usage(plan)
    assert len(findings) == 1


def test_coordinate_frame_present_silences_compass_finding():
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["intent"] = plan["intent"] + " Fillet added on the east side."
    plan["coordinate_frame"] = {"east": "-x"}
    assert check_coordinate_frame_usage(plan) == []


def test_no_compass_word_emits_nothing():
    assert check_coordinate_frame_usage(VALID_PLAN) == []


# ---- hinge/pivot intent without joints -----------------------------------------


def test_hinge_language_no_joints_flags():
    plan = _joints_plan()
    del plan["joints"]
    del plan["root_part"]
    plan["intent"] = "A cradle that folds flat against the plate, " + plan["intent"]
    findings = check_hinge_intent_without_joints(plan)
    assert len(findings) == 1


def test_hinge_language_with_joints_not_flagged():
    plan = _joints_plan()
    plan["intent"] = "A cradle that folds flat against the plate, " + plan["intent"]
    assert check_hinge_intent_without_joints(plan) == []


def test_hinge_language_single_part_exempt():
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["intent"] = "A lid that folds flat, " + plan["intent"]
    assert check_hinge_intent_without_joints(plan) == []


def test_no_hinge_language_emits_nothing():
    plan = _joints_plan()
    del plan["joints"]
    del plan["root_part"]
    assert check_hinge_intent_without_joints(plan) == []


# ---- positional shared-interface detection (unnamed round mates) ---------------


def _round_interface(pid_plan, pid, position_mm, diameter_mm, placement=None):
    for part in pid_plan["parts"]:
        if part["id"] == pid:
            part["interfaces"] = [
                {"type": "pin_bore", "position_mm": position_mm, "diameter_mm": diameter_mm}
            ]
            if placement is not None:
                part["placement"] = placement
    return pid_plan


def test_unnamed_coincident_round_interfaces_flagged():
    plan = _joints_plan()
    del plan["joints"]
    del plan["root_part"]
    _round_interface(plan, "door", [0, 0, 0], 5.0)
    _round_interface(plan, "wall", [0, 0, 0], 5.0)
    findings = check_shared_interfaces(plan)
    assert len(findings) == 1
    assert "door" in findings[0] and "wall" in findings[0]


def test_positional_finding_silenced_by_joints_entry():
    plan = _joints_plan()
    _round_interface(plan, "door", [0, 0, 0], 5.0)
    _round_interface(plan, "wall", [0, 0, 0], 5.0)
    assert check_shared_interfaces(plan) == []


def test_positional_different_diameters_not_flagged():
    plan = _joints_plan()
    del plan["joints"]
    del plan["root_part"]
    _round_interface(plan, "door", [0, 0, 0], 5.0)
    _round_interface(plan, "wall", [0, 0, 0], 20.0)
    assert check_shared_interfaces(plan) == []


def test_positional_different_positions_not_flagged():
    plan = _joints_plan()
    del plan["joints"]
    del plan["root_part"]
    _round_interface(plan, "door", [0, 0, 0], 5.0)
    _round_interface(plan, "wall", [100, 0, 0], 5.0)
    assert check_shared_interfaces(plan) == []


def test_positional_check_skips_interfaces_without_position_or_diameter():
    plan = _joints_plan()
    del plan["joints"]
    del plan["root_part"]
    plan["parts"][0]["interfaces"] = [{"type": "pin_bore", "diameter_mm": 5.0}]
    plan["parts"][1]["interfaces"] = [{"type": "pin_bore", "position_mm": [0, 0, 0]}]
    assert check_shared_interfaces(plan) == []


def test_positional_coincidence_after_placement_transform():
    """Two interfaces at different authored-frame positions that land at the same
    assembled-frame point once each part's placement is applied still flag."""
    plan = _joints_plan()
    del plan["joints"]
    del plan["root_part"]
    _round_interface(plan, "door", [0, 0, 0], 5.0)
    _round_interface(plan, "wall", [10, 0, 0], 5.0, placement={"translate_mm": [-10, 0, 0]})
    findings = check_shared_interfaces(plan)
    assert len(findings) == 1


# ---- intent_ts reconciliation -------------------------------------------


def _log_plan(*entries, intent_ts=None):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["request_log"] = [
        {"ts": "2026-07-19T10:00:00Z", "kind": "initial", "text": "Make an enclosure"},
        *entries,
    ]
    if intent_ts is not None:
        plan["intent_ts"] = intent_ts
    return plan


_FIX = {"ts": "2026-07-19T11:00:00Z", "kind": "correction", "text": "5mm taller"}


def test_initial_only_needs_no_intent_ts(plan_file):
    assert validate_plan(plan_file(_log_plan())) == []


def test_unreconciled_correction_fails(plan_file):
    errors = validate_plan(plan_file(_log_plan(_FIX, intent_ts="2026-07-19T10:00:00Z")))
    assert len(errors) == 1 and "5mm taller" in errors[0]


def test_missing_intent_ts_with_entries_fails(plan_file):
    errors = validate_plan(plan_file(_log_plan(_FIX)))
    assert any("not reconciled" in e for e in errors)


def test_intent_ts_equal_to_newest_entry_passes(plan_file):
    assert validate_plan(plan_file(_log_plan(_FIX, intent_ts=_FIX["ts"]))) == []


def test_unparseable_intent_ts_fails(plan_file):
    errors = validate_plan(plan_file(_log_plan(_FIX, intent_ts="yesterday")))
    assert any("not an ISO-8601" in e for e in errors)


CASES = Path(__file__).resolve().parent.parent / "evals" / "cases"


def test_summary_renders_every_eval_plan():
    for plan_path in sorted(CASES.glob("*/BUILD_PLAN.json")):
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        text = summarize(plan, plan_path)
        for part in plan["parts"]:
            assert f"| {part['id']} |" in text, plan_path


def test_summary_load_pose_interfaces_and_policy(tmp_path):
    plan = {
        "material": "PETG",
        "nozzle_mm": 0.4,
        "review_policy": "minimal",
        "optimize_for": "visual_quality",
        "constraints": {"wall_min_mm": 1.2, "overhang_max_deg": 45, "dimension_tolerance_mm": 0.5},
        "parts": [
            {
                "id": "base",
                "description": "foot | pad",
                "dimensions": {"w_mm": 40, "d_mm": 30, "h_mm": 5.5},
                "load": {"type": "compression"},
                "pose_intent": "sits at origin",
                "blocks_needed": [{"name": "hollow_box", "extents_mm": [1, 2, 3]}, "port_cutout"],
                "interfaces": [
                    {
                        "type": "port_cutout",
                        "name": "usb",
                        "wall": "south",
                        "position_mm": [1, 0, 2.5],
                    }
                ],
            }
        ],
    }
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert (
        r"| 1 | base | foot \| pad | 40 x 30 x 5.5 | compression | sits at origin "
        "| hollow_box, port_cutout |" in text
    )
    assert "`base` show_face inferred" in text
    assert "**Review policy:** `minimal`" in text
    assert "| base | usb | port_cutout |  | south | 1,0,2.5 |" in text


def _base_plan(**overrides) -> dict:
    plan = {
        "material": "PETG",
        "nozzle_mm": 0.4,
        "constraints": {"wall_min_mm": 1.2, "overhang_max_deg": 45, "dimension_tolerance_mm": 0.5},
        "parts": [
            {
                "id": "bracket",
                "description": "mounting bracket",
                "dimensions": {"w_mm": 40, "d_mm": 30, "h_mm": 5},
                "interfaces": [{"type": "hole", "name": "hole_2", "position_mm": [1, 0, 0]}],
            }
        ],
    }
    plan.update(overrides)
    return plan


def test_open_questions_section_present_for_plain_and_bulleted_lines(tmp_path):
    plan = _base_plan(
        planning_notes="OPEN: hinge pin diameter unverified\n- OPEN: unclear if lid snaps or screws"
    )
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Open questions**" in text
    assert "- OPEN: hinge pin diameter unverified" in text
    assert "- OPEN: unclear if lid snaps or screws" in text


def test_open_questions_section_absent_when_no_open_lines(tmp_path):
    plan = _base_plan(planning_notes="the enclosure stays open on the east face")
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Open questions**" not in text


def test_names_i_chose_flags_unmatched_and_skips_matched(tmp_path):
    plan = _base_plan(
        request_log=[
            {"ts": "2026-01-01T00:00:00Z", "kind": "initial", "text": "add a hole for a screw"}
        ]
    )
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Names I chose**" in text
    assert "`bracket` (part)" in text
    assert "`hole_2`" not in text.split("**Names I chose**", 1)[1]


def test_names_i_chose_absent_without_request_log(tmp_path):
    plan = _base_plan()
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Names I chose**" not in text


def test_load_cases_table_rendered_with_derivation(tmp_path):
    plan = _base_plan(
        planning_notes="LOAD_MASS: bracket 187 g sf=2.0",
    )
    plan["parts"][0]["load"] = {
        "dir": [0, 0, -1],
        "magnitude_n": 3.67,
        "applied_at": "hole_2",
        "grounded_at": ["hole_2"],
    }
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Load cases**" in text
    assert "| bracket | 187 g | 2.0 | 3.67 N | hole_2 | hole_2 |" in text


def test_load_cases_table_shows_applied_dir_override(tmp_path):
    plan = _base_plan(planning_notes="LOAD_MASS: bracket 187 g sf=2.0")
    plan["parts"][0]["load"] = {
        "dir": [0, 0, -1],
        "magnitude_n": 3.67,
        "applied_at": "hole_2",
        "applied_dir": [0, -0.5, -1],
        "grounded_at": ["hole_2"],
    }
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "hole_2 dir=0,-0.5,-1" in text


def test_load_cases_section_omitted_when_no_magnitude(tmp_path):
    plan = _base_plan()
    plan["parts"][0]["load"] = {"dir": [0, 0, -1]}
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Load cases**" not in text


def test_load_cases_missing_mass_note_shows_unspecified(tmp_path):
    plan = _base_plan()
    plan["parts"][0]["load"] = {"dir": [0, 0, -1], "magnitude_n": 1.0}
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "| bracket | (unspecified) | (unspecified) | 1 N |" in text


PARAMS_PLAN: dict[str, Any] = {
    "schema_version": 1,
    "intent": (
        "Open-top enclosure for an Arduino Nano, single body with 1.2 mm walls and a "
        "USB-C pass-through on the front wall; board seats on internal standoffs."
    ),
    "printer": "Bambu P1S",
    "material": "PLA",
    "nozzle_mm": 0.4,
    "parts": [
        {
            "id": "body",
            "description": "Main enclosure body",
            "dimensions": {"w_mm": 385, "d_mm": 120, "h_mm": 20},
            "interfaces": [],
            "blocks_needed": ["hollow_box"],
        }
    ],
    "constraints": {
        "wall_min_mm": 1.2,
        "overhang_max_deg": 45,
        "dimension_tolerance_mm": 1.0,
    },
}

SCRIPT_SOURCE = """
import cadquery as cq
from blocks import hollow_box

# PARAMETERS
width = 390.0  # mm
depth = 120  # mm, unchanged
wall = 2.4  # not a plan field
add_bosses = True

inner = width - 2 * wall
port = hollow_box(width, depth, 20, wall, 2.0, 0.0)

result = port
"""


@pytest.fixture
def script_file(tmp_path):
    def _write(source):
        p = tmp_path / "body.py"
        p.write_text(source)
        return str(p)

    return _write


def test_parse_numeric_literals(script_file):
    path = script_file(SCRIPT_SOURCE)
    parsed = parse_parameters(path)
    assert parsed["width"] == 390.0
    assert parsed["depth"] == 120
    assert parsed["wall"] == 2.4


def test_computed_and_call_assignments_skipped(script_file):
    path = script_file(SCRIPT_SOURCE)
    parsed = parse_parameters(path)
    assert "inner" not in parsed
    assert "port" not in parsed
    assert "result" not in parsed


def test_bool_assignment_skipped(script_file):
    path = script_file(SCRIPT_SOURCE)
    parsed = parse_parameters(path)
    assert "add_bosses" not in parsed


def test_syntax_error_reported_not_crashed(script_file):
    path = script_file("def broken(:\n")
    report = run(path, "body", "nonexistent.json", write=False)
    assert report["errors"]
    assert "parse" in report["errors"][0].lower()


def test_changed_dimension_diffed():
    parsed = {"width": 390}
    diff = reconcile(parsed, PARAMS_PLAN, "body")
    assert diff["changed"] == [{"field": "w_mm", "from": 385, "to": 390}]


def test_unchanged_dimension_reported():
    parsed = {"depth": 120}
    diff = reconcile(parsed, PARAMS_PLAN, "body")
    assert diff["changed"] == []
    assert diff["unchanged"] == ["d_mm"]


def test_unmapped_parameter_surfaced():
    parsed = {"wall": 3.0, "boss_dia": 6}
    diff = reconcile(parsed, PARAMS_PLAN, "body")
    assert diff["changed"] == []
    assert diff["unchanged"] == []
    assert sorted(diff["unmapped"]) == ["boss_dia", "wall"]


def test_missing_part_errors(script_file, plan_file):
    script_path = script_file(SCRIPT_SOURCE)
    plan_path = plan_file(PARAMS_PLAN)
    report = run(script_path, "nonexistent_part", plan_path, write=False)
    assert report["errors"]
    assert "nonexistent_part" in report["errors"][0]


def test_dry_run_leaves_file_untouched(script_file, plan_file):
    script_path = script_file(SCRIPT_SOURCE)
    plan_path = plan_file(PARAMS_PLAN)
    with open(plan_path, encoding="utf-8") as f:
        before = f.read()

    report = run(script_path, "body", plan_path, write=False)

    with open(plan_path, encoding="utf-8") as f:
        after = f.read()
    assert before == after
    assert report["written"] is False
    assert report["changed"] == [{"field": "w_mm", "from": 385, "to": 390}]


def test_valid_write_updates_plan(script_file, plan_file):
    script_path = script_file(SCRIPT_SOURCE)
    plan_path = plan_file(PARAMS_PLAN)

    report = run(script_path, "body", plan_path, write=True)

    assert report["written"] is True
    assert report["errors"] == []
    with open(plan_path, encoding="utf-8") as f:
        updated = json.load(f)
    assert updated["parts"][0]["dimensions"]["w_mm"] == 390


def test_invalid_write_refused(script_file, plan_file):
    bad_script = script_file("width = -5.0\n")
    plan_path = plan_file(PARAMS_PLAN)
    with open(plan_path, encoding="utf-8") as f:
        before = f.read()

    report = run(bad_script, "body", plan_path, write=True)

    assert report["written"] is False
    assert report["errors"]
    with open(plan_path, encoding="utf-8") as f:
        after = f.read()
    assert before == after


def test_missing_plan_file_errors(script_file, tmp_path):
    script_path = script_file(SCRIPT_SOURCE)
    missing_plan = str(tmp_path / "does_not_exist.json")
    report = run(script_path, "body", missing_plan, write=False)
    assert report["errors"]


def test_bom_row_valid(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["bom"] = [{"item": "heat-set insert", "spec": "M3-0.5-6", "qty": 4, "parts": ["body"]}]
    assert validate_plan(plan_file(plan)) == []


def test_bom_row_unknown_key_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["bom"] = [{"item": "screw", "parts": ["body"], "price": 0.10}]
    errors = validate_plan(plan_file(plan))
    assert any("bom" in e for e in errors)


def test_bom_row_zero_qty_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["bom"] = [{"item": "screw", "parts": ["body"], "qty": 0}]
    errors = validate_plan(plan_file(plan))
    assert any("bom" in e for e in errors)


def test_bom_row_unknown_part_id_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["bom"] = [{"item": "screw", "parts": ["lid"]}]
    errors = validate_plan(plan_file(plan))
    assert any("lid" in e for e in errors)


def test_bom_coverage_flags_unlisted_part():
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["blocks_needed"] = ["heat_set_boss"]
    findings = check_bom_coverage(plan, _INVENTORY_PATH)
    assert any("body" in f and "heat_set_boss" in f for f in findings)


def test_bom_coverage_silent_when_part_listed():
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["blocks_needed"] = ["heat_set_boss"]
    plan["bom"] = [{"item": "heat-set insert", "parts": ["body"]}]
    assert check_bom_coverage(plan, _INVENTORY_PATH) == []


def test_bom_coverage_silent_for_non_hardware_block():
    assert check_bom_coverage(VALID_PLAN, _INVENTORY_PATH) == []


def test_summary_bom_table_rendered(tmp_path):
    plan = _base_plan(
        bom=[
            {
                "item": "heat-set insert",
                "spec": "M3-0.5-6",
                "qty": 4,
                "parts": ["bracket"],
                "note": "press fit",
            }
        ]
    )
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Non-printed hardware**" in text
    assert "| heat-set insert | M3-0.5-6 | 4 | bracket | press fit |" in text


def test_summary_bom_table_omitted_without_bom(tmp_path):
    plan = _base_plan()
    text = summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Non-printed hardware**" not in text


def test_inventory_hardware_blocks_carry_supplied_hardware():
    inventory = json.loads(Path(_INVENTORY_PATH).read_text())
    by_name = {b["name"]: b for b in inventory}
    for name in (
        "screw_boss",
        "pcb_standoff",
        "heat_set_boss",
        "hex_nut_trap",
        "counterbore_hole",
        "countersink_hole",
        "pin_hinge",
    ):
        assert by_name[name].get("supplied_hardware"), f"{name} missing supplied_hardware"
    assert "supplied_hardware" not in by_name["fillet_box"]


def _copy_plan(**copy_of):
    return {
        **VALID_PLAN_TWO_PARTS,
        "parts": [
            VALID_PLAN_TWO_PARTS["parts"][0],  # type: ignore[index]
            {**VALID_PLAN_TWO_PARTS["parts"][1], "copy_of": copy_of},  # type: ignore[index]
        ],
    }


def test_copy_of_mirrored_valid(plan_file):
    assert validate_plan(plan_file(_copy_plan(part="body", mirror="X"))) == []


def test_copy_of_bad_mirror_axis_rejected(plan_file):
    errors = validate_plan(plan_file(_copy_plan(part="body", mirror="W")))
    assert any("Schema error" in e for e in errors)


def test_copy_of_unknown_source(plan_file):
    errors = validate_plan(plan_file(_copy_plan(part="ghost")))
    assert any("ghost" in e for e in errors)


def test_copy_of_self(plan_file):
    errors = validate_plan(plan_file(_copy_plan(part="lid")))
    assert any("itself" in e for e in errors)


def test_copy_of_chained(plan_file):
    plan = _copy_plan(part="body")
    plan["parts"][0] = {**plan["parts"][0], "copy_of": {"part": "lid"}}
    errors = validate_plan(plan_file(plan))
    assert any("is itself a copy" in e for e in errors)


def test_copy_of_multi_union_source(plan_file):
    plan = _copy_plan(part="body")
    plan["parts"][0] = {**plan["parts"][0], "unions": [{"id": "a"}, {"id": "b"}]}
    errors = validate_plan(plan_file(plan))
    assert any("unions" in e for e in errors)
