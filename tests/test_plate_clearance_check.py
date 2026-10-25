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
from conftest import box_stl

import quality_gate
from plate_clearance_check import run_plate_clearance_check


def _plan(parts, nozzle_mm=0.4):
    return {"nozzle_mm": nozzle_mm, "parts": parts}


def _two_on_one_plate(tmp_path, cx):
    """Two unions sharing plate 'shared'; box B placed so the gap is cx - 10 mm."""
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (cx, 0, 0))
    return _plan([{"id": "a", "plate": "shared"}, {"id": "b", "plate": "shared"}])


def _clearance_issues(issues):
    return [i for i in issues if i["type"] == "plate_clearance"]


def test_multi_union_part_co_plated_unions_flagged(tmp_path):
    """Two unions of ONE part sharing a plate are grouped and clearance-checked, just like
    two separate parts -- the per-union plate grouping uses the shared union expansion."""
    box_stl(tmp_path / "leaf_a.stl", (0, 0, 0))
    box_stl(tmp_path / "leaf_b.stl", (10.1, 0, 0))  # gap 0.1 < 0.2 layer height
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


def _object_plan(tmp_path, cx):
    """Two unions of one part in slicer object 'knob'; box B centred at (cx, 0, 0)."""
    box_stl(tmp_path / "body.stl", (0, 0, 0))
    box_stl(tmp_path / "ring.stl", (cx, 0, 0))
    unions = [{"id": "body", "object": "knob"}, {"id": "ring", "object": "knob"}]
    return _plan([{"id": "knob_part", "unions": unions}])


def test_touching_object_members_pass(tmp_path):
    issues = run_plate_clearance_check(_object_plan(tmp_path, 10.0), str(tmp_path))
    assert [i for i in issues if i["severity"] == "error"] == []


def test_overlapping_object_members_flagged(tmp_path):
    issues = run_plate_clearance_check(_object_plan(tmp_path, 8.0), str(tmp_path))
    (issue,) = [i for i in issues if i["severity"] == "error"]
    assert issue["type"] == "object_member_overlap"
    assert issue["severity"] == "error"
    assert issue["object"] == "knob"
    assert issue["overlap_mm3"] == pytest.approx(200.0, rel=0.01)


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
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (10.1, 0, 0))  # close, but not co-plated
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


# ---- freshness: stale exported STL --------------------------------------------


def _write_scripts_and_manifest(tmp_path, hashes):
    """Write <id>.py for each id in `hashes`, then an export manifest whose recorded
    stamp for each union is `hashes[id]` (a real current-content hash, or a bogus one to
    simulate staleness)."""
    from freshness import MANIFEST_FILENAME

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir(exist_ok=True)
    manifest: dict = {
        "exported_at": "2026-01-01T00:00:00+00:00",
        "unions": {},
        "keep_out_zones": {},
    }
    for uid, stamp in hashes.items():
        (parts_dir / f"{uid}.py").write_text("result = 1\n", encoding="utf-8")
        manifest["unions"][uid] = {"part_id": uid, "source_script_hash": stamp}
    (tmp_path / MANIFEST_FILENAME).write_text(json.dumps(manifest), encoding="utf-8")
    return str(parts_dir)


def test_stale_union_flagged_and_excluded_from_pair_check(tmp_path):
    from freshness import script_hash

    plan = _two_on_one_plate(tmp_path, cx=10.1)  # would otherwise flag plate_clearance
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "b.py").write_text("result = 1\n", encoding="utf-8")
    b_hash = script_hash(str(tmp_path / "parts" / "b.py"))
    parts_dir_str = _write_scripts_and_manifest(tmp_path, {"a": "0" * 64, "b": b_hash})

    issues = run_plate_clearance_check(plan, str(tmp_path), parts_dir=parts_dir_str)

    stale = [i for i in issues if i["type"] == "stale_artifact"]
    assert len(stale) == 1
    assert stale[0]["union"] == "a"
    assert stale[0]["severity"] == "error"
    # Fewer than two fresh unions remain on the plate -> no pairwise clearance check.
    assert _clearance_issues(issues) == []


def test_fresh_manifest_passes_through_unaffected(tmp_path):

    plan = _two_on_one_plate(tmp_path, cx=10.1)  # gap 0.1 < 0.2 -> should still flag
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    (parts_dir / "a.py").write_text("result = 1\n", encoding="utf-8")
    (parts_dir / "b.py").write_text("result = 2\n", encoding="utf-8")
    from freshness import write_manifest

    write_manifest(
        str(tmp_path),
        {
            "a": ("a", str(parts_dir / "a.py")),
            "b": ("b", str(parts_dir / "b.py")),
        },
    )

    issues = run_plate_clearance_check(plan, str(tmp_path), parts_dir=str(parts_dir))

    assert [i for i in issues if i["type"] == "stale_artifact"] == []
    assert len(_clearance_issues(issues)) == 1


def test_missing_stl_degrades_to_warning(tmp_path):
    # Plate declared with two unions but no exported STLs yet. Without --parts-dir the
    # freshness check also degrades, so both warnings are present.
    plan = _plan([{"id": "a", "plate": "shared"}, {"id": "b", "plate": "shared"}])
    issues = run_plate_clearance_check(plan, str(tmp_path))
    assert {i["type"] for i in issues} == {"check_skipped"}
    assert all(i["severity"] == "warning" for i in issues)
    assert any("assembled union STL not found" in i["message"] for i in issues)


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
            "intent": (
                "Plate clearance gate fixture: two parts co-plated on one build plate, "
                "laid out as planned to exercise the co-plated union clearance check."
            ),
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
