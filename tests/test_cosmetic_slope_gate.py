"""Tests for the cosmetic-slope quality-gate stage (quality_gate._run_cosmetic_slope_stage).

Fast: exercises the stage's intent-gating and thresholding directly on a synthetic
orientation result -- no CadQuery, no mesh work (that lives in test_mesh_io.py).
"""

import quality_gate

_ABOVE = quality_gate.COSMETIC_SLOPE_MIN_AREA_MM2 + 100.0
_BELOW = quality_gate.COSMETIC_SLOPE_MIN_AREA_MM2 - 1.0


def _plan(plan_mode=None, part_mode=None, part_id="body"):
    part = {"id": part_id}
    if part_mode:
        part["optimize_for"] = part_mode
    plan = {"parts": [part]}
    if plan_mode:
        plan["optimize_for"] = plan_mode
    return plan


def test_visual_part_flags_cosmetic_slope():
    issues = quality_gate._run_cosmetic_slope_stage(
        _plan(plan_mode="visual_quality"), "build/body.py", {"cosmetic_slope_area_mm2": _ABOVE}
    )
    assert len(issues) == 1
    assert issues[0]["source"] == "cosmetic_slope"
    assert issues[0]["type"] == "cosmetic_slope"
    assert issues[0]["severity"] == "warning"  # advisory: never fails the gate
    assert issues[0]["area_mm2"] == _ABOVE


def test_below_threshold_no_finding():
    assert (
        quality_gate._run_cosmetic_slope_stage(
            _plan(plan_mode="visual_quality"), "build/body.py", {"cosmetic_slope_area_mm2": _BELOW}
        )
        == []
    )


def test_non_visual_part_is_noop():
    for mode in ("strength", "min_support", "min_build_height"):
        assert (
            quality_gate._run_cosmetic_slope_stage(
                _plan(plan_mode=mode), "build/body.py", {"cosmetic_slope_area_mm2": _ABOVE}
            )
            == []
        )


def test_per_part_visual_override_runs_under_strength_plan():
    issues = quality_gate._run_cosmetic_slope_stage(
        _plan(plan_mode="strength", part_mode="visual_quality"),
        "build/body.py",
        {"cosmetic_slope_area_mm2": _ABOVE},
    )
    assert len(issues) == 1
    assert issues[0]["type"] == "cosmetic_slope"


def test_missing_orientation_skips():
    issues = quality_gate._run_cosmetic_slope_stage(
        _plan(plan_mode="visual_quality"), "build/body.py", None
    )
    assert len(issues) == 1
    assert issues[0]["type"] == "check_skipped"
    assert issues[0]["severity"] == "warning"


def test_orientation_without_metric_field_skips():
    issues = quality_gate._run_cosmetic_slope_stage(
        _plan(plan_mode="visual_quality"), "build/body.py", {"rotate": []}
    )
    assert len(issues) == 1
    assert issues[0]["type"] == "check_skipped"


def test_unknown_script_is_noop():
    assert (
        quality_gate._run_cosmetic_slope_stage(
            _plan(plan_mode="visual_quality", part_id="other"),
            "build/body.py",
            {"cosmetic_slope_area_mm2": _ABOVE},
        )
        == []
    )
