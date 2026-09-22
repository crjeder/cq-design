"""Tests for toolpath_speed.py: the corner/crowding print-time advisor."""

import math
import os
import sys

import cadquery as cq
import pytest
import trimesh

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

import toolpath_speed as ts  # noqa: E402

MOTION = {
    "v_cruise_mm_s": 200.0,
    "accel_mm_s2": 5000.0,
    "junction_deviation_mm": 0.05,
    "min_layer_time_s": 5.0,
    "layer_height_mm": 0.2,
    "line_width_mm": 0.42,
    "infill_density": 0.15,
}


# ---------------------------------------------------------------------------
# R_eff continuity at the sharp/filleted boundary
# ---------------------------------------------------------------------------


def test_r_eff_straight_is_unbounded():
    assert math.isinf(ts._r_eff_sharp(0.0, 0.05))


def test_r_eff_reversal_approaches_zero():
    r = ts._r_eff_sharp(math.radians(179.9), 0.05)
    assert 0 < r < 1e-3


def test_r_eff_matches_known_90deg_value():
    r = ts._r_eff_sharp(math.radians(90.0), 0.05)
    assert r == pytest.approx(0.1207, rel=1e-3)


def test_v_corner_agrees_at_boundary():
    # A sharp corner's R_eff and a fillet of that same radius must score identically --
    # the two cases are one continuous formula, not a rule with exceptions.
    r_eff = ts._r_eff_sharp(math.radians(90.0), 0.05)
    v_sharp = ts.v_corner(r_eff, 5000.0, 200.0)
    v_fillet = ts.v_corner(r_eff, 5000.0, 200.0)
    assert v_sharp == v_fillet


def test_v_corner_monotonic_in_radius():
    speeds = [ts.v_corner(r, 5000.0, 200.0) for r in [0.121, 0.5, 2.0, 5.0, 100.0]]
    assert speeds == sorted(speeds)
    assert speeds[-1] == 200.0


# ---------------------------------------------------------------------------
# Three-term time decomposition
# ---------------------------------------------------------------------------


def _box_model(size, fillet_r=None, jd=0.05) -> dict:
    wp = cq.Workplane("XY").box(*size)
    if fillet_r:
        wp = wp.edges("|Z").fillet(fillet_r)
    model = ts.extract_corner_model(wp, jd)
    assert model is not None
    return model


def test_terms_sum_to_actual_time():
    model = _box_model([20.0, 20.0, 10.0])
    t = ts.compute_path_times(model["corners"], model["wall_lengths_mm"], 5000.0, 200.0)
    assert t["T_ideal"] + t["T_corners"] + t["T_crowding"] == pytest.approx(t["T_actual"], rel=1e-9)


def test_crowding_is_never_negative():
    # Small box: corners are close together relative to the accel distance.
    model = _box_model([6.0, 6.0, 10.0])
    t = ts.compute_path_times(model["corners"], model["wall_lengths_mm"], 5000.0, 200.0)
    assert t["T_crowding"] >= -1e-9


def test_filleted_box_has_higher_efficiency_than_sharp():
    sharp = ts.compute_path_times(
        *(lambda m: (m["corners"], m["wall_lengths_mm"]))(_box_model([20.0, 20.0, 10.0])),
        5000.0,
        200.0,
    )
    filleted = ts.compute_path_times(
        *(lambda m: (m["corners"], m["wall_lengths_mm"]))(
            _box_model([20.0, 20.0, 10.0], fillet_r=3.0)
        ),
        5000.0,
        200.0,
    )
    assert filleted["speed_efficiency"] > sharp["speed_efficiency"]


def test_large_sparse_part_is_efficient():
    model = _box_model([200.0, 200.0, 50.0], fillet_r=20.0)
    t = ts.compute_path_times(model["corners"], model["wall_lengths_mm"], 5000.0, 200.0)
    assert t["speed_efficiency"] > 0.9


# ---------------------------------------------------------------------------
# B-rep extraction correctness: bores excluded, fillets exact
# ---------------------------------------------------------------------------


def test_fillet_radius_and_wall_length_are_exact():
    model = _box_model([20.0, 20.0, 10.0], fillet_r=3.0)
    assert len(model["corners"]) == 4
    for c in model["corners"]:
        assert c.kind == "fillet"
        assert c.r_eff_mm == pytest.approx(3.0)
    assert all(w == pytest.approx(14.0) for w in model["wall_lengths_mm"])


def test_bore_is_excluded_as_an_inner_wire():
    wp = cq.Workplane("XY").box(20.0, 20.0, 10.0).faces(">Z").workplane().hole(4.0)
    model = ts.extract_corner_model(wp, 0.05)
    assert model is not None
    assert len(model["corners"]) == 4
    assert all(c.kind == "sharp" for c in model["corners"])
    assert all(w == pytest.approx(20.0) for w in model["wall_lengths_mm"])


def test_height_coverage_is_full_for_a_prismatic_box():
    model = _box_model([20.0, 20.0, 10.0])
    assert model["height_coverage"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Leave-one-out attribution
# ---------------------------------------------------------------------------


def test_attribution_recovers_positive_time_for_sharp_corners():
    model = _box_model([20.0, 20.0, 10.0])
    rows = ts.attribute_corners(model["corners"], model["wall_lengths_mm"], 5000.0, 200.0)
    assert len(rows) == 4
    assert all(r["time_recovered_s"] > 0 for r in rows)


def test_attribution_is_symmetric_for_identical_corners():
    model = _box_model([20.0, 20.0, 10.0])
    rows = ts.attribute_corners(model["corners"], model["wall_lengths_mm"], 5000.0, 200.0)
    values = [r["time_recovered_s"] for r in rows]
    assert max(values) == pytest.approx(min(values), rel=1e-6)


# ---------------------------------------------------------------------------
# Stall detection
# ---------------------------------------------------------------------------


def test_short_layer_path_stalls():
    box = trimesh.creation.box([8.0, 8.0, 40.0])
    result = ts.layer_time_model(box, MOTION, speed_efficiency=0.8, perimeters=2)
    assert result["status"] == "ok"
    assert result["stalled"] is True
    # Stalled: total time is height-driven only.
    n_layers = 40.0 / MOTION["layer_height_mm"]
    assert result["total_time_s"] == pytest.approx(n_layers * MOTION["min_layer_time_s"], rel=1e-6)


def test_long_layer_path_does_not_stall():
    box = trimesh.creation.box([100.0, 100.0, 40.0])
    result = ts.layer_time_model(box, MOTION, speed_efficiency=0.8, perimeters=2)
    assert result["status"] == "ok"
    assert result["stalled"] is False


# ---------------------------------------------------------------------------
# Findings survive a stall, with reworded rationale and zeroed time-recovery framing
# ---------------------------------------------------------------------------


def test_corner_finding_survives_a_stall():
    model = _box_model([8.0, 8.0, 40.0])
    times = ts.compute_path_times(model["corners"], model["wall_lengths_mm"], 5000.0, 200.0)
    layer = {"status": "ok", "stalled": True, "total_time_s": 1000.0}
    finding = ts.build_finding(
        "part1", "u1", times, model["corners"], model["wall_lengths_mm"], 5000.0, 200.0, layer
    )
    assert finding is not None
    assert finding["stalled"] is True
    assert "vibration" in finding["message"] or "wear" in finding["message"]
    assert "stall_remedies" in finding


def test_finding_omitted_above_reporting_threshold():
    model = _box_model([200.0, 200.0, 50.0], fillet_r=20.0)
    times = ts.compute_path_times(model["corners"], model["wall_lengths_mm"], 5000.0, 200.0)
    finding = ts.build_finding(
        "part1", "u1", times, model["corners"], model["wall_lengths_mm"], 5000.0, 200.0, None
    )
    assert finding is None


def test_crowding_dominant_finding_has_no_table():
    # Well-filleted (low corner tax) but small (short walls never reach cruise): the
    # dominant loss term is crowding, not any single sharp edge.
    model = _box_model([8.0, 8.0, 10.0], fillet_r=3.0)
    times = ts.compute_path_times(model["corners"], model["wall_lengths_mm"], 5000.0, 200.0)
    assert times["T_crowding"] > times["T_corners"]
    finding = ts.build_finding(
        "part1", "u1", times, model["corners"], model["wall_lengths_mm"], 5000.0, 200.0, None
    )
    assert finding is not None
    assert "attribution" not in finding
    assert finding.get("dominant") == "crowding"


# ---------------------------------------------------------------------------
# Skip paths
# ---------------------------------------------------------------------------


def test_run_check_skips_without_motion_block():
    result = ts.run_toolpath_speed_check({"parts": []}, "unused.py", motion=None)
    assert result["status"] == "skipped"
    assert "motion" in result["reason"]
