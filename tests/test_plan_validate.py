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


def test_invalid_optimize_for_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["optimize_for"] = "speed"
    errors = validate_plan(plan_file(plan))
    assert any("optimize_for" in e for e in errors)


def test_valid_show_face(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["show_face"] = {"dir": [0, 0, 1]}
    assert validate_plan(plan_file(plan)) == []


def test_zero_show_face_direction_rejected(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["show_face"] = {"dir": [0, 0, 0]}
    errors = validate_plan(plan_file(plan))
    assert any("non-zero direction" in e for e in errors)


def test_missing_dimensions(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    del plan["parts"][0]["dimensions"]
    errors = validate_plan(plan_file(plan))
    assert any("dimensions" in e for e in errors)


def test_missing_required_top_level(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    del plan["material"]
    errors = validate_plan(plan_file(plan))
    assert any("material" in e for e in errors)


def test_empty_parts_array(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"] = []
    errors = validate_plan(plan_file(plan))
    assert len(errors) >= 1


def test_unknown_block_name(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN))
    plan["parts"][0]["blocks_needed"] = ["nonexistent_block_xyz"]
    errors = validate_plan(plan_file(plan))
    assert any("nonexistent_block_xyz" in e for e in errors)


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
    # pin_hinge's dof axis is +Y; a Z wish is not parallel.
    plan = _plan_with_joint(axis_dir="Z")
    errors = validate_plan(plan_file(plan))
    assert any("not parallel" in e for e in errors)


def test_contract_revolute_parallel_but_off_line_rejected(plan_file):
    # Axis parallel (+Y) but the pivot is off the block's axis line -> not coaxial.
    plan = _plan_with_joint(axis_dir="Y", axis_origin_mm=[5, 0, 0])
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
