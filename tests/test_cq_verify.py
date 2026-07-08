"""Unit tests for the cq_verify construction-time assertions."""

import cadquery as cq
import pytest

import cq_verify

# ---- verify_boolean ----


def test_effective_cut_passes():
    body = cq.Workplane("XY").box(20, 20, 20)
    tool = cq.Workplane("XY").box(5, 5, 30)  # overlaps -> real material removed
    after = cq_verify.verify_boolean(body, body.cut(tool), "cut", "slot")
    assert after is not None


def test_true_noop_cut_raises():
    body = cq.Workplane("XY").box(20, 20, 20)
    # Tool sits far away in +X, no overlap -> cut removes nothing.
    tool = cq.Workplane("XY").transformed(offset=(100, 0, 0)).box(5, 5, 5)
    with pytest.raises(RuntimeError) as exc:
        cq_verify.verify_boolean(body, body.cut(tool), "cut", "vent_slot")
    msg = str(exc.value)
    assert "cq-verify:silent_boolean:vent_slot" in msg


def test_equal_volume_relocation_passes():
    # Same shape translated: volume and face count unchanged, but the centroid moves,
    # so it is NOT a no-op and must not raise.
    before = cq.Workplane("XY").box(10, 10, 10)
    after_wp = cq.Workplane("XY").transformed(offset=(50, 0, 0)).box(10, 10, 10)
    assert cq_verify.verify_boolean(before, after_wp, "union", "moved") is after_wp


# ---- verify_feature_bounds ----


def test_feature_within_bounds_passes():
    base = cq.Workplane("XY").box(20, 20, 20)
    grown = base.faces(">Z").workplane().rect(5, 5).extrude(-3)  # stays inside footprint
    assert cq_verify.verify_feature_bounds(base, grown, "pocket") is grown


def test_feature_overflow_raises():
    base = cq.Workplane("XY").box(20, 20, 20)
    # Union a boss that sticks out well past +X.
    boss = cq.Workplane("XY").transformed(offset=(18, 0, 0)).box(10, 4, 4)
    grown = base.union(boss)
    with pytest.raises(RuntimeError) as exc:
        cq_verify.verify_feature_bounds(base, grown, "tab", tolerance=0.1)
    assert "cq-verify:feature_overflow:tab" in str(exc.value)


# ---- check_workplane ----


def test_workplane_on_anchor_passes():
    wp = cq.Workplane("XY").workplane(offset=12)
    assert cq_verify.check_workplane(wp, "lid_top", expected_origin=(0, 0, 12)) is wp


def test_workplane_drift_raises():
    wp = cq.Workplane("XY").center(5, 7)  # origin permanently shifted
    with pytest.raises(RuntimeError) as exc:
        cq_verify.check_workplane(wp, "lid_top", expected_origin=(0, 0, 0))
    assert "cq-verify:workplane_drift:lid_top" in str(exc.value)


def test_workplane_no_expected_origin_is_noop():
    wp = cq.Workplane("XY").center(5, 7)
    assert cq_verify.check_workplane(wp, "x") is wp  # no expected_origin -> never raises
