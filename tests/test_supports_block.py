"""Tests for blocks.breakaway_fin / place_fin."""

from typing import cast

import cadquery as cq
import pytest

from blocks import breakaway_fin, place_fin
from blocks.supports import STANDOFF_MM, TINE_OVERLAP_MM, _tine_levels


def _s(wp):
    return cast(cq.Shape, wp.val())


def test_fin_is_one_valid_solid_with_expected_envelope():
    fin = breakaway_fin(height=10, length=12)
    bb = _s(fin).BoundingBox()
    assert _s(fin).isValid()
    assert len(fin.solids().vals()) == 1
    assert bb.xlen == pytest.approx(12.0, abs=1e-3)
    assert bb.zlen == pytest.approx(10.0, abs=1e-3)
    # wall thickness 0.8 behind y=0, tines reach standoff + overlap past it
    assert bb.ymax == pytest.approx(STANDOFF_MM + TINE_OVERLAP_MM, abs=1e-3)
    assert bb.ymin == pytest.approx(-0.8, abs=1e-3)


def test_tine_crosses_standoff_gap():
    fin = breakaway_fin(height=10, length=12, layer_h=0.2)
    z = _tine_levels(10, 0.2)[0] + 0.1
    assert _s(fin).isInside(cq.Vector(0, STANDOFF_MM / 2, z))
    assert not _s(fin).isInside(cq.Vector(0, STANDOFF_MM / 2, z + 0.2))


def test_tine_levels_scale_with_height_and_start_dense():
    short, tall = _tine_levels(10, 0.2), _tine_levels(40, 0.2)
    assert len(tall) > len(short) >= 5
    assert tall[:5] == short[:5]


def test_top_edges_are_rounded():
    fin = breakaway_fin(height=10, length=12, tine_w=0.4, wall_t=0.8)
    bb = _s(fin).BoundingBox()
    # a sharp-cornered top would contain this point; a fillet does not
    assert not _s(fin).isInside(cq.Vector(0, -0.8 + 0.01, bb.zmax - 0.01))
    assert _s(fin).isInside(cq.Vector(0, -0.4, bb.zmax - 0.05))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"height": 0, "length": 5},
        {"height": 10, "length": -1},
        {"height": 10, "length": 5, "tine_w": 0.3},
        {"height": 10, "length": 5, "tine_w": 0.9},
        {"height": 1, "length": 5},
    ],
)
def test_invalid_parameters_raise(kwargs):
    with pytest.raises(ValueError, match="fin_invalid"):
        breakaway_fin(**kwargs)


def test_collision_with_body_is_rejected():
    body = cq.Workplane("XY").box(20, 20, 20, centered=(True, False, False)).translate((0, -5, 0))
    with pytest.raises(ValueError, match="fin_collision"):
        breakaway_fin(height=10, length=12, body=body)


def test_body_past_standoff_only_touches_tines():
    body = cq.Workplane("XY").box(20, 20, 20, centered=(True, False, False)).translate((0, 0.2, 0))
    fin = breakaway_fin(height=10, length=12, body=body)
    assert _s(fin).isValid()


def test_place_fin_puts_top_on_anchor_and_faces_outward():
    fin = place_fin(breakaway_fin(height=10, length=12), (10, 0, 20), (1, 0, 0))
    bb = _s(fin).BoundingBox()
    assert bb.zmax == pytest.approx(20.0, abs=1e-3)
    assert bb.zmin == pytest.approx(10.0, abs=1e-3)
    # wall lies on the outward (+X) side of the anchor, tines reach to it
    assert bb.xmax == pytest.approx(10.8 + STANDOFF_MM - 0.2 + 0.0, abs=0.3)
    assert bb.xmin < 10.0
