"""Tests for the keep-out-zone validation stage.

Fixtures use trimesh-generated box STLs (no CadQuery) so the suite stays fast. Zone STLs
follow the `keep_out__<part_id>__<zone_name>.stl` naming convention `write_assembly` writes
and `keep_out_check` discovers -- built here with `units.keep_out_stl_name` so the tests
can't drift from the real naming convention.
"""

import json
import sys

from conftest import box_stl

import quality_gate
from keep_out_check import run_keep_out_check
from units import keep_out_stl_name


def _zone_stl(stl_dir, part_id, zone_name, center, extents=(4, 4, 4)):
    box_stl(stl_dir / keep_out_stl_name(part_id, zone_name), center, extents)


def _plan(part_ids):
    return {"parts": [{"id": p} for p in part_ids]}


def _violations(issues):
    return [i for i in issues if i["type"] == "keep_out_violation"]


# ---- foreign union intrudes ---------------------------------------------------


def test_foreign_union_intruding_on_zone_flagged(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))  # declaring part's own union: x in [-5, 5]
    box_stl(tmp_path / "b.stl", (12, 0, 0))  # foreign union: x in [7, 17]
    _zone_stl(tmp_path, "a", "clearance", (9, 0, 0))  # zone: x in [7, 11] -> overlaps b only
    issues = run_keep_out_check(_plan(["a", "b"]), str(tmp_path))
    flagged = _violations(issues)
    assert len(flagged) == 1
    assert flagged[0]["source"] == "geometry"
    assert flagged[0]["severity"] == "error"
    assert flagged[0]["offending_union"] == "b"
    assert flagged[0]["zone_part"] == "a"
    assert flagged[0]["zone_name"] == "clearance"


# ---- no union intrudes ---------------------------------------------------------


def test_no_intrusion_passes(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))  # x in [-5, 5]
    box_stl(tmp_path / "b.stl", (30, 0, 0))  # x in [25, 35], nowhere near the zone
    _zone_stl(tmp_path, "a", "clearance", (0, 0, 0))  # x in [-2, 2], inside a's own union
    issues = run_keep_out_check(_plan(["a", "b"]), str(tmp_path))
    assert _violations(issues) == []


# ---- declaring part's own union is excluded ------------------------------------


def test_declaring_parts_own_union_excluded(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))  # x in [-5, 5]
    # Zone anchored flush against a's own union: x in [4, 8], overlaps a at [4, 5].
    _zone_stl(tmp_path, "a", "clearance", (6, 0, 0))
    issues = run_keep_out_check(_plan(["a"]), str(tmp_path))
    assert _violations(issues) == []


def test_a_different_parts_zone_still_checks_against_first_part(tmp_path):
    """The self-exclusion only applies to the zone's OWN declaring part; a zone
    declared by a different part still checks against this part's union."""
    box_stl(tmp_path / "a.stl", (0, 0, 0))  # x in [-5, 5]
    box_stl(tmp_path / "b.stl", (30, 0, 0))  # x in [25, 35]
    # Zone declared by "b", but anchored so it overlaps "a" instead.
    _zone_stl(tmp_path, "b", "reserved", (0, 0, 0))
    issues = run_keep_out_check(_plan(["a", "b"]), str(tmp_path))
    flagged = _violations(issues)
    assert len(flagged) == 1
    assert flagged[0]["offending_union"] == "a"
    assert flagged[0]["zone_part"] == "b"


# ---- no zones declared: geometry stack is never even imported -----------------


def test_no_zones_declared_returns_empty_without_backend(tmp_path, monkeypatch):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (30, 0, 0))
    monkeypatch.setitem(sys.modules, "trimesh", None)
    assert run_keep_out_check(_plan(["a", "b"]), str(tmp_path)) == []


# ---- dependency-missing degrades to a single check_skipped warning -------------


def test_backend_missing_degrades_to_warning(tmp_path, monkeypatch):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    _zone_stl(tmp_path, "a", "clearance", (0, 0, 0))
    monkeypatch.setitem(sys.modules, "trimesh", None)
    issues = run_keep_out_check(_plan(["a"]), str(tmp_path))
    assert len(issues) == 1
    assert issues[0]["type"] == "check_skipped"
    assert issues[0]["severity"] == "warning"


def test_missing_foreign_stl_degrades_to_warning(tmp_path):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    _zone_stl(tmp_path, "a", "clearance", (0, 0, 0))
    # "b" is a declared part but its STL was never exported. Without --parts-dir the
    # freshness check also degrades, so both warnings are present.
    issues = run_keep_out_check(_plan(["a", "b"]), str(tmp_path))
    assert {i["type"] for i in issues} == {"check_skipped"}
    assert all(i["severity"] == "warning" for i in issues)
    assert any("assembled union STL not found" in i["message"] for i in issues)


# ---- freshness: stale exported STL ---------------------------------------------


def _write_manifest(tmp_path, unions=None, keep_out_zones=None):
    from freshness import MANIFEST_FILENAME

    manifest = {
        "exported_at": "2026-01-01T00:00:00+00:00",
        "unions": unions or {},
        "keep_out_zones": keep_out_zones or {},
    }
    (tmp_path / MANIFEST_FILENAME).write_text(json.dumps(manifest), encoding="utf-8")


def test_stale_foreign_union_flagged_and_excluded(tmp_path):
    from freshness import script_hash

    # Foreign union "b" intrudes on a's zone; if b's STL were validated it would flag.
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (12, 0, 0))
    _zone_stl(tmp_path, "a", "clearance", (9, 0, 0))

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    (parts_dir / "a.py").write_text("result = 1\n", encoding="utf-8")
    (parts_dir / "b.py").write_text("result = 2\n", encoding="utf-8")
    _write_manifest(
        tmp_path,
        unions={
            "a": {"part_id": "a", "source_script_hash": script_hash(str(parts_dir / "a.py"))},
            "b": {"part_id": "b", "source_script_hash": "0" * 64},  # stale
        },
    )

    issues = run_keep_out_check(_plan(["a", "b"]), str(tmp_path), parts_dir=str(parts_dir))

    stale = [i for i in issues if i["type"] == "stale_artifact"]
    assert len(stale) == 1
    assert stale[0]["union"] == "b"
    # b excluded from the intersection check -> no violation reported for it.
    assert _violations(issues) == []


def test_stale_zone_flagged_and_excluded(tmp_path):
    from freshness import script_hash

    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (12, 0, 0))
    _zone_stl(tmp_path, "a", "clearance", (9, 0, 0))

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    (parts_dir / "a.py").write_text("result = 1\n", encoding="utf-8")
    (parts_dir / "b.py").write_text("result = 2\n", encoding="utf-8")
    _write_manifest(
        tmp_path,
        unions={
            "a": {"part_id": "a", "source_script_hash": script_hash(str(parts_dir / "a.py"))},
            "b": {"part_id": "b", "source_script_hash": script_hash(str(parts_dir / "b.py"))},
        },
        keep_out_zones={"a::clearance": {"part_id": "a", "source_script_hash": "0" * 64}},
    )

    issues = run_keep_out_check(_plan(["a", "b"]), str(tmp_path), parts_dir=str(parts_dir))

    stale = [i for i in issues if i["type"] == "stale_artifact"]
    assert len(stale) == 1
    assert stale[0]["zone_name"] == "clearance"
    assert stale[0]["zone_part"] == "a"
    assert _violations(issues) == []


def test_fresh_manifest_passes_through_unaffected(tmp_path):
    from freshness import script_hash

    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (12, 0, 0))
    _zone_stl(tmp_path, "a", "clearance", (9, 0, 0))

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    (parts_dir / "a.py").write_text("result = 1\n", encoding="utf-8")
    (parts_dir / "b.py").write_text("result = 2\n", encoding="utf-8")
    _write_manifest(
        tmp_path,
        unions={
            "a": {"part_id": "a", "source_script_hash": script_hash(str(parts_dir / "a.py"))},
            "b": {"part_id": "b", "source_script_hash": script_hash(str(parts_dir / "b.py"))},
        },
        keep_out_zones={
            "a::clearance": {
                "part_id": "a",
                "source_script_hash": script_hash(str(parts_dir / "a.py")),
            }
        },
    )

    issues = run_keep_out_check(_plan(["a", "b"]), str(tmp_path), parts_dir=str(parts_dir))

    assert [i for i in issues if i["type"] == "stale_artifact"] == []
    assert len(_violations(issues)) == 1


# ---- gate integration: a violation blocks a clean pass -------------------------


def test_gate_surfaces_keep_out_violation(tmp_path, good_script):
    box_stl(tmp_path / "a.stl", (0, 0, 0))
    box_stl(tmp_path / "b.stl", (12, 0, 0))
    _zone_stl(tmp_path, "a", "clearance", (9, 0, 0))
    plan = {
        "schema_version": 1,
        "intent": (
            "Keep-out gate fixture: two boxes with a declared clearance zone between them, "
            "assembled as planned to exercise the whole-model keep-out check."
        ),
        "printer": "Bambu P1S",
        "material": "PLA",
        "nozzle_mm": 0.4,
        "constraints": {
            "wall_min_mm": 1.2,
            "overhang_max_deg": 45,
            "dimension_tolerance_mm": 0.3,
        },
        "parts": [
            {
                "id": "a",
                "description": "box a",
                "dimensions": {"w_mm": 10, "d_mm": 10, "h_mm": 10},
                "interfaces": [],
                "blocks_needed": [],
            },
            {
                "id": "b",
                "description": "box b",
                "dimensions": {"w_mm": 10, "d_mm": 10, "h_mm": 10},
                "interfaces": [],
                "blocks_needed": [],
            },
        ],
    }
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(plan))

    report = quality_gate.run_gate(
        str(good_script),
        str(plan_path),
        allow_fix=False,
        stl_dir=str(tmp_path),
    )
    assert report["passed"] is False
    assert len(_violations(report["issues"])) == 1

    # The finding renders into the fix prompt the auto-fixer would see.
    prompt = quality_gate._render_fix_prompt(str(good_script), report["issues"])
    assert "keep_out_violation" in prompt
