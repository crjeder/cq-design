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
    text = plan_summary.summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Open questions**" in text
    assert "- OPEN: hinge pin diameter unverified" in text
    assert "- OPEN: unclear if lid snaps or screws" in text


def test_open_questions_section_absent_when_no_open_lines(tmp_path):
    plan = _base_plan(planning_notes="the enclosure stays open on the east face")
    text = plan_summary.summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Open questions**" not in text


def test_names_i_chose_flags_unmatched_and_skips_matched(tmp_path):
    plan = _base_plan(
        request_log=[
            {"ts": "2026-01-01T00:00:00Z", "kind": "initial", "text": "add a hole for a screw"}
        ]
    )
    text = plan_summary.summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Names I chose**" in text
    assert "`bracket` (part)" in text
    assert "`hole_2`" not in text.split("**Names I chose**", 1)[1]


def test_names_i_chose_absent_without_request_log(tmp_path):
    plan = _base_plan()
    text = plan_summary.summarize(plan, tmp_path / "BUILD_PLAN.json")
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
    text = plan_summary.summarize(plan, tmp_path / "BUILD_PLAN.json")
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
    text = plan_summary.summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "hole_2 dir=0,-0.5,-1" in text


def test_load_cases_section_omitted_when_no_magnitude(tmp_path):
    plan = _base_plan()
    plan["parts"][0]["load"] = {"dir": [0, 0, -1]}
    text = plan_summary.summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "**Load cases**" not in text


def test_load_cases_missing_mass_note_shows_unspecified(tmp_path):
    plan = _base_plan()
    plan["parts"][0]["load"] = {"dir": [0, 0, -1], "magnitude_n": 1.0}
    text = plan_summary.summarize(plan, tmp_path / "BUILD_PLAN.json")
    assert "| bracket | (unspecified) | (unspecified) | 1 N |" in text
