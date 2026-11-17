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


# ---- verify_stage ----


def test_stage_bbox_match_passes():
    body = cq.Workplane("XY").box(20, 10, 5, centered=(True, True, False))
    assert cq_verify.verify_stage(body, "base_shell", bbox=(-10, 10, -5, 5, 0, 5)) is body


def test_stage_bbox_mismatch_raises():
    body = cq.Workplane("XY").box(20, 10, 5, centered=(True, True, False))
    with pytest.raises(RuntimeError) as exc:
        cq_verify.verify_stage(body, "base_shell", bbox=(-10, 10, -5, 5, 0, 50))
    assert "cq-verify:stage_mismatch:base_shell" in str(exc.value)


def test_stage_volume_above_minimum_passes():
    body = cq.Workplane("XY").box(20, 20, 20)
    assert cq_verify.verify_stage(body, "bossed", vol_min=100) is body


def test_stage_volume_below_minimum_raises():
    body = cq.Workplane("XY").box(20, 20, 20)
    with pytest.raises(RuntimeError) as exc:
        cq_verify.verify_stage(body, "bossed", vol_min=1e9)
    assert "cq-verify:stage_mismatch:bossed" in str(exc.value)


def test_stage_requires_bbox_or_vol_min():
    body = cq.Workplane("XY").box(20, 20, 20)
    with pytest.raises(ValueError):
        cq_verify.verify_stage(body, "bossed")


# verify_seated: C5 hinge-ear geometry -- knuckle disc centered at Z=13.5, r=2.6
# (spans Z 10.9..16.1); riser box below it. axis "-z" = boss toward support.
_KNUCKLE = cq.Workplane("YZ").circle(2.6).extrude(10).translate((-5, 5, 13.5))


def _riser_topping_at(z_top: float):
    return cq.Workplane("XY").box(10, 4, 5).translate((0, 3, z_top - 2.5))


def test_seated_at_center_raises():
    riser = _riser_topping_at(13.5)  # top face on the disc's CENTER
    with pytest.raises(RuntimeError, match=r"boss_swallowed:hinge_ear"):
        cq_verify.verify_seated(riser, _KNUCKLE, "-z", label="hinge_ear")


def test_seated_at_tangent_passes():
    riser = _riser_topping_at(10.9)  # top face on the disc's tangent
    assert cq_verify.verify_seated(riser, _KNUCKLE, "-z", label="hinge_ear") is _KNUCKLE


def test_seated_deliberate_embed_within_overlap_passes():
    riser = _riser_topping_at(11.4)  # 0.5 mm embed, under the 1.0 mm default
    assert cq_verify.verify_seated(riser, _KNUCKLE, "-z", label="hinge_ear") is _KNUCKLE


def test_seated_rejects_bad_axis():
    with pytest.raises(ValueError):
        cq_verify.verify_seated(_riser_topping_at(10.9), _KNUCKLE, "down")


# ---- check_fillet / check_chamfer / check_ligament ----


def _box():
    return cq.Workplane("XY").box(20, 20, 5)


def test_fillet_too_large_raises():
    with pytest.raises(RuntimeError) as exc:
        cq_verify.check_fillet(_box(), 6, ">Z", "lid_edge")
    assert "cq-verify:fillet_radius:lid_edge" in str(exc.value)
    assert "limit 5.00" in str(exc.value)


def test_fillet_valid_returns_body():
    body = _box()
    assert cq_verify.check_fillet(body, 2, ">Z", "lid_edge") is body


def test_fillet_vertical_edges_use_long_neighbours():
    body = _box()
    assert cq_verify.check_fillet(body, 3, "|Z", "corners") is body
    with pytest.raises(RuntimeError):
        cq_verify.check_fillet(body, 10, "|Z", "corners")


def test_fillet_all_edges_halves_short_edge():
    with pytest.raises(RuntimeError):
        cq_verify.check_fillet(_box(), 2.5)


def test_fillet_accepted_radius_builds():
    body = cq_verify.check_fillet(_box(), 4.5, ">Z")
    assert body.edges(">Z").fillet(4.5).val().isValid()


def test_chamfer_too_large_and_valid():
    body = _box()
    with pytest.raises(RuntimeError) as exc:
        cq_verify.check_chamfer(body, 5, ">Z", "top_chamfer")
    assert "cq-verify:chamfer_size:top_chamfer" in str(exc.value)
    assert cq_verify.check_chamfer(body, 1, ">Z", "top_chamfer") is body


def test_ligament():
    with pytest.raises(RuntimeError) as exc:
        cq_verify.check_ligament(6, 5, 1.2, "m5_boss")
    assert "cq-verify:thin_ligament:m5_boss" in str(exc.value)
    assert cq_verify.check_ligament(10, 5, 1.2, "m5_boss") == 2.5


# ---- stage recorder ----


def test_recorder_off_by_default():
    body = cq.Workplane("XY").box(20, 20, 20)
    cq_verify.verify_boolean(body, body.cut(cq.Workplane("XY").box(5, 5, 30)), "cut", "slot")
    assert cq_verify.stop_stage_recording() == []


def test_recorder_captures_delta_per_label():
    body = cq.Workplane("XY").box(20, 20, 20)
    cq_verify.start_stage_recording()
    cut = cq_verify.verify_boolean(body, body.cut(cq.Workplane("XY").box(4, 4, 30)), "cut", "slot")
    cq_verify.verify_boolean(body, cut, "cut", "slot")  # same label: first wins
    cq_verify.verify_stage(cut, "base", bbox=(-10, 10, -10, 10, -10, 10))
    recs = cq_verify.stop_stage_recording()
    assert [r["name"] for r in recs] == ["slot", "base"]
    slot = recs[0]
    assert slot["operation"] == "cut"
    assert slot["bbox"] == pytest.approx([-2, 2, -2, 2, -10, 10])
    assert slot["volume_mm3"] == pytest.approx(4 * 4 * 20)
    assert recs[1]["operation"] == "stage"
