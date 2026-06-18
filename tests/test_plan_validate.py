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
            "interfaces": [
                {"type": "port_cutout", "connector": "usb_c", "wall": "front"}
            ],
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
    "assembly": {"strategy": "snap_fit", "clearance_mm": 0.3},
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


def test_two_parts_missing_assembly(plan_file):
    plan = json.loads(json.dumps(VALID_PLAN_TWO_PARTS))
    del plan["assembly"]
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
    plan["parts"][0]["blocks_needed"] = [
        {"name": "fillet_box", "extents_mm": [0.8, 35, 20]}
    ]
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
