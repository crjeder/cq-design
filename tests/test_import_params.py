"""Tests for import_params.py (fast tier, no CadQuery)."""

import json
import os
import sys
from typing import Any

import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

from import_params import parse_parameters, reconcile, run  # noqa: E402

VALID_PLAN: dict[str, Any] = {
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


@pytest.fixture
def plan_file(tmp_path):
    def _write(plan):
        p = tmp_path / "BUILD_PLAN.json"
        p.write_text(json.dumps(plan))
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
    diff = reconcile(parsed, VALID_PLAN, "body")
    assert diff["changed"] == [{"field": "w_mm", "from": 385, "to": 390}]


def test_unchanged_dimension_reported():
    parsed = {"depth": 120}
    diff = reconcile(parsed, VALID_PLAN, "body")
    assert diff["changed"] == []
    assert diff["unchanged"] == ["d_mm"]


def test_unmapped_parameter_surfaced():
    parsed = {"wall": 3.0, "boss_dia": 6}
    diff = reconcile(parsed, VALID_PLAN, "body")
    assert diff["changed"] == []
    assert diff["unchanged"] == []
    assert sorted(diff["unmapped"]) == ["boss_dia", "wall"]


def test_missing_part_errors(script_file, plan_file):
    script_path = script_file(SCRIPT_SOURCE)
    plan_path = plan_file(VALID_PLAN)
    report = run(script_path, "nonexistent_part", plan_path, write=False)
    assert report["errors"]
    assert "nonexistent_part" in report["errors"][0]


def test_dry_run_leaves_file_untouched(script_file, plan_file):
    script_path = script_file(SCRIPT_SOURCE)
    plan_path = plan_file(VALID_PLAN)
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
    plan_path = plan_file(VALID_PLAN)

    report = run(script_path, "body", plan_path, write=True)

    assert report["written"] is True
    assert report["errors"] == []
    with open(plan_path, encoding="utf-8") as f:
        updated = json.load(f)
    assert updated["parts"][0]["dimensions"]["w_mm"] == 390


def test_invalid_write_refused(script_file, plan_file):
    bad_script = script_file("width = -5.0\n")
    plan_path = plan_file(VALID_PLAN)
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
