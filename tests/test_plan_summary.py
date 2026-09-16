"""Tests for src/plan_summary.py -- fast, no CadQuery."""

import json
from pathlib import Path

import plan_summary

CASES = Path(__file__).resolve().parent.parent / "evals" / "cases"


def test_summary_renders_every_eval_plan():
    for plan_path in sorted(CASES.glob("*/BUILD_PLAN.json")):
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        text = plan_summary.summarize(plan, plan_path)
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
    text = plan_summary.summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert (
        r"| 1 | base | foot \| pad | 40 x 30 x 5.5 | compression | sits at origin "
        "| hollow_box, port_cutout |" in text
    )
    assert "`base` show_face inferred" in text
    assert "**Review policy:** `minimal`" in text
    assert "| base | usb | port_cutout |  | south | 1,0,2.5 |" in text
