"""End-to-end test: a stale exported STL surfaces as `stale_artifact` through the gate.

Exercises `quality_gate.run_gate`'s wiring of `parts_dir` into the whole-model check
stages (kinematic/plate-clearance/keep-out), using the plate-clearance stage since it
needs no CadQuery-exported joint mesh -- just two co-plated union STLs.
"""

import json

from conftest import box_stl

import quality_gate


def _plan():
    part = {
        "id": "a",
        "description": "box a",
        "dimensions": {"w_mm": 10, "d_mm": 10, "h_mm": 10},
        "interfaces": [],
        "blocks_needed": [],
        "plate": "shared",
    }
    other = {**part, "id": "b"}
    return {
        "schema_version": 1,
        "intent": (
            "Gate freshness fixture: two identical co-plated parts on one shared plate, "
            "printed as-is to exercise the provenance-stamp comparison path."
        ),
        "printer": "Bambu P1S",
        "material": "PLA",
        "nozzle_mm": 0.4,
        "parts": [part, other],
        "constraints": {
            "wall_min_mm": 1.2,
            "overhang_max_deg": 45,
            "dimension_tolerance_mm": 0.3,
        },
    }


def test_stale_export_surfaces_through_gate(tmp_path, good_script):
    from freshness import MANIFEST_FILENAME, script_hash

    stl_dir = good_script.parent  # same dir the gate defaults stl_dir/parts_dir to
    # Co-plated boxes close enough to fail clearance if both were validated.
    box_stl(stl_dir / "a.stl", (0, 0, 0))
    box_stl(stl_dir / "b.stl", (10.05, 0, 0))

    (stl_dir / "a.py").write_text("result = 1\n", encoding="utf-8")
    (stl_dir / "b.py").write_text("result = 2\n", encoding="utf-8")
    manifest = {
        "exported_at": "2026-01-01T00:00:00+00:00",
        "unions": {
            "a": {"part_id": "a", "source_script_hash": script_hash(str(stl_dir / "a.py"))},
            "b": {"part_id": "b", "source_script_hash": "0" * 64},  # stale
        },
        "keep_out_zones": {},
    }
    (stl_dir / MANIFEST_FILENAME).write_text(json.dumps(manifest), encoding="utf-8")

    plan_path = stl_dir / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan()))

    report = quality_gate.run_gate(
        str(good_script),
        str(plan_path),
        allow_fix=False,
        stl_dir=str(stl_dir),
    )

    stale = [i for i in report["issues"] if i["type"] == "stale_artifact"]
    assert len(stale) == 1
    assert stale[0]["union"] == "b"
    assert stale[0]["severity"] == "error"
    assert report["passed"] is False
    # "b" excluded from the pairwise comparison -> no plate_clearance finding either.
    assert [i for i in report["issues"] if i["type"] == "plate_clearance"] == []
