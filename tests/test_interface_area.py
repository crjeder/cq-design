"""interface_area: B-rep join area between a placed tool and the body so far."""

import os
import sys

import cadquery as cq
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from interface_area import interface_area  # noqa: E402

CUBE = cq.Workplane("XY").box(20, 20, 20, centered=(True, True, False)).val()
BASE_AREA = 3.141592653589793 * 3**2


def cone(x, z):
    return cq.Solid.makeCone(3, 0.5, 5, cq.Vector(x, 0, z))


def test_cone_on_face_is_base_area():
    area, c = interface_area(CUBE, cone(0, 20))
    assert area == pytest.approx(BASE_AREA, rel=1e-3)
    assert c[2] == pytest.approx(20)


def test_sunk_cone_is_cross_section_not_sunk_surface():
    area, _ = interface_area(CUBE, cone(0, 19.9))
    assert area == pytest.approx(3.141592653589793 * 2.95**2, rel=1e-2)


def test_cone_centred_on_edge_is_half_base():
    area, _ = interface_area(CUBE, cone(10, 20))
    assert area == pytest.approx(BASE_AREA / 2, rel=1e-3)


def test_cone_beyond_edge_is_zero():
    area, _ = interface_area(CUBE, cone(13, 20))
    assert area == 0.0


def test_post_on_three_slivers():
    grid = cq.Workplane("XY").box(0.2, 1, 1, centered=False)
    for i in (1, 2):
        grid = grid.union(
            cq.Workplane("XY").box(0.2, 1, 1, centered=False).translate((i * 2, 0, 0))
        )
    grid_shape = grid.val()
    post = cq.Workplane("XY").box(6, 3, 5, centered=False).translate((-0.5, -1, 1)).val()
    area, _ = interface_area(grid_shape, post)
    assert area == pytest.approx(0.6, rel=1e-3)


def test_post_on_column():
    column = cq.Solid.makeCylinder(1.5, 5, cq.Vector(0, 0, 20))
    area, _ = interface_area(CUBE, column)
    assert area == pytest.approx(3.141592653589793 * 1.5**2, rel=1e-3)


def test_through_pin_is_not_zero():
    plate = cq.Workplane("XY").box(20, 20, 2, centered=(True, True, False)).val()
    pin = cq.Solid.makeCylinder(1.5, 6, cq.Vector(0, 0, -2))
    area, _ = interface_area(plate, pin)
    assert area >= 3.141592653589793 * 1.5**2 - 1e-3
