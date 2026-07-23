"""Tests for the plate-clearance validation stage.

Fixtures use trimesh-generated box STLs (no CadQuery) so the unit tests stay fast. Two
axis-aligned 10 mm boxes share a plate; box A spans x[-5, 5], box B is centred at
(cx, 0, 0) so the surface gap is cx - 10. With the default nozzle (0.4 mm) the threshold
is one layer height = 0.2 mm. STLs are assembled-pose per-union meshes, as the model
export would emit.
"""

import json
import sys

import pytest
import trimesh

import quality_gate
from plate_clearance_check import run_plate_clearance_check


def _box_stl(path, center):
    mesh = trimesh.creation.box(extents=(10, 10, 10))
    mesh.apply_translation(center)
    mesh.export(str(path))


def _plan(parts, nozzle_mm=0.4):
    return {"nozzle_mm": nozzle_mm, "parts": parts}


def _two_on_one_plate(tmp_path, cx):
    """Two unions sharing plate 'shared'; box B placed so the gap is cx - 10 mm."""
    _box_stl(tmp_path / "a.stl", (0, 0, 0))
    _box_stl(tmp_path / "b.stl", (cx, 0, 0))
    return _plan([{"id": "a", "plate": "shared"}, {"id": "b", "plate": "shared"}])


def _clearance_issues(issues):
    return [i for i in issues if i["type"] == "plate_clearance"]


def test_multi_union_part_co_plated_unions_flagged(tmp_path):
    """Two unions of ONE part sharing a plate are grouped and clearance-checked, just like
    two separate parts -- the per-union plate grouping uses the shared union expansion."""
    _box_stl(tmp_path / "leaf_a.stl", (0, 0, 0))
    _box_stl(tmp_path / "leaf_b.stl", (10.1, 0, 0))  # gap 0.1 < 0.2 layer height
    plan = _plan(
        [
            {
                "id": "hinge",
                "unions": [
                    {"id": "leaf_a", "plate": "shared"},
                    {"id": "leaf_b", "plate": "shared"},
                ],
            }
        ]
    )
    flagged = _clearance_issues(run_plate_clearance_check(plan, str(tmp_path)))
    assert len(flagged) == 1
    assert {flagged[0]["union_a"], flagged[0]["union_b"]} == {"leaf_a", "leaf_b"}


# ---- 3.1 pair below threshold flagged ----------------------------------------


def test_pair_below_threshold_flagged(tmp_path):
    plan = _two_on_one_plate(tmp_path, cx=10.1)  # gap 0.1 < 0.2
    issues = run_plate_clearance_check(plan, str(tmp_path))
    flagged = _clearance_issues(issues)
    assert len(flagged) == 1
    issue = flagged[0]
    assert issue["source"] == "geometry"
    assert issue["severity"] == "error"
    assert issue["plate"] == "shared"
    assert {issue["union_a"], issue["union_b"]} == {"a", "b"}
    assert issue["gap_mm"] == pytest.approx(0.1, abs=1e-3)
    assert issue["threshold_mm"] == 0.2


# ---- 3.2 pair above threshold passes -----------------------------------------


def test_pair_above_threshold_passes(tmp_path):
    plan = _two_on_one_plate(tmp_path, cx=10.6)  # gap 0.6 > 0.2
    issues = run_plate_clearance_check(plan, str(tmp_path))
    assert _clearance_issues(issues) == []
    assert not [i for i in issues if i["severity"] == "error"]


# ---- 3.3 gap exactly at threshold flagged (at-or-below boundary) -------------


def test_gap_exactly_at_threshold_flagged(tmp_path):
    plan = _two_on_one_plate(tmp_path, cx=10.2)  # gap == 0.2 == threshold
    issues = run_plate_clearance_check(plan, str(tmp_path))
    flagged = _clearance_issues(issues)
    assert len(flagged) == 1
    assert flagged[0]["gap_mm"] == pytest.approx(0.2, abs=1e-3)


# ---- 3.4 single-union and all-separate plates skipped ------------------------


def test_single_union_plate_skipped(tmp_path):
    # Two parts, each on its own (implicit) plate -> no co-plated pair to compare.
    _box_stl(tmp_path / "a.stl", (0, 0, 0))
    _box_stl(tmp_path / "b.stl", (10.1, 0, 0))  # close, but not co-plated
    plan = _plan([{"id": "a"}, {"id": "b"}])
    issues = run_plate_clearance_check(plan, str(tmp_path))
    assert issues == []


def test_no_multi_union_plate_returns_empty_without_backend(tmp_path, monkeypatch):
    # With no multi-union plate the geometry stack must not even be imported.
    monkeypatch.setitem(sys.modules, "trimesh", None)
    plan = _plan([{"id": "a"}, {"id": "b"}])
    assert run_plate_clearance_check(plan, str(tmp_path)) == []


# ---- 3.5 dependency-missing degrades to a single check_skipped warning --------


def test_backend_missing_degrades_to_warning(tmp_path, monkeypatch):
    plan = _two_on_one_plate(tmp_path, cx=10.1)
    monkeypatch.setitem(sys.modules, "trimesh", None)  # `import trimesh` -> ImportError
    issues = run_plate_clearance_check(plan, str(tmp_path))
    assert len(issues) == 1
    assert issues[0]["type"] == "check_skipped"
    assert issues[0]["severity"] == "warning"


def test_missing_stl_degrades_to_warning(tmp_path):
    # Plate declared with two unions but no exported STLs yet.
    plan = _plan([{"id": "a", "plate": "shared"}, {"id": "b", "plate": "shared"}])
    issues = run_plate_clearance_check(plan, str(tmp_path))
    assert len(issues) == 1
    assert issues[0]["type"] == "check_skipped"
    assert issues[0]["severity"] == "warning"


# ---- 3.6 gate integration: too-close pair blocks a clean pass ----------------


def test_gate_surfaces_plate_clearance(tmp_path, good_script):
    plan = _two_on_one_plate(tmp_path, cx=10.1)
    # The gate validates the plan first and SKIPS the plate-clearance stage if that
    # fails, so this gate-routed plan must be schema-complete (unlike the minimal `_plan`
    # the direct run_plate_clearance_check tests use). Fill the required top-level and
    # per-part fields.
    plan.update(
        {
            "schema_version": 1,
            "intent": "plate clearance gate fixture",
            "printer": "Bambu P1S",
            "material": "PLA",
            "constraints": {
                "wall_min_mm": 1.2,
                "overhang_max_deg": 45,
                "dimension_tolerance_mm": 0.3,
            },
        }
    )
    for part in plan["parts"]:
        part.update(
            {
                "description": "co-plated box",
                "dimensions": {"w_mm": 10, "d_mm": 10, "h_mm": 10},
                "interfaces": [],
                "blocks_needed": [],
            }
        )
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(plan))

    report = quality_gate.run_gate(
        str(good_script),
        str(plan_path),
        allow_fix=False,
        stl_dir=str(tmp_path),
    )
    assert report["passed"] is False
    clearance = _clearance_issues(report["issues"])
    assert len(clearance) == 1

    # The finding renders into the fix prompt the auto-fixer would see.
    prompt = quality_gate._render_fix_prompt(str(good_script), report["issues"])
    assert "plate_clearance" in prompt
