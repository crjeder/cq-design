# mypy: ignore-errors
# type: ignore  # CAD/trimesh stub-union noise; tests are ruff-linted, not type-checked
"""Tests for the cq_warehouse copy-patch neutralization shim (cq_compat)."""

import cadquery as cq
import pytest
from cadquery.occ_impl.shapes import Shape

from cq_compat import import_cq_warehouse_extensions


def test_shim_restores_native_copy_and_keeps_insert_hole():
    """After the shim runs, extensions side effects are present but Shape.copy is native."""
    import_cq_warehouse_extensions()

    assert hasattr(cq.Workplane, "insertHole")  # cq_warehouse side effect installed
    # Native methods live in cadquery; the cq_warehouse patch lives in cq_warehouse.extensions.
    assert Shape.copy.__module__ == "cadquery.occ_impl.shapes"
    assert Shape._apply_transform.__module__ == "cadquery.occ_impl.shapes"


def test_shim_is_idempotent():
    """Repeated calls leave Shape.copy native and unchanged."""
    import_cq_warehouse_extensions()
    first = Shape.copy
    import_cq_warehouse_extensions()
    assert Shape.copy is first
    assert Shape.copy.__module__ == "cadquery.occ_impl.shapes"


def test_copy_and_transform_do_not_deepcopy(monkeypatch):
    """Copy/rotate/translate must not route through __setstate__ (the BinTools round-trip
    that crashes on OCCT 7.8). A tripwire on __setstate__ proves the native path is used."""
    import_cq_warehouse_extensions()

    def tripwire(self, data):
        raise AssertionError("__setstate__ called -> deepcopy/BinTools path is active")

    monkeypatch.setattr(Shape, "__setstate__", tripwire)

    box = cq.Workplane("XY").box(10, 10, 10)
    box.val().copy()
    rotated = box.rotate((0, 0, 0), (1, 0, 0), 90)
    moved = rotated.translate((1, 2, 3))

    assert moved.val().isValid()


def test_transformed_shape_exports_valid_stl(tmp_path):
    """End-to-end: with the shim active, a rotated solid exports to a watertight STL."""
    import trimesh

    import_cq_warehouse_extensions()

    out = tmp_path / "box.stl"
    box = cq.Workplane("XY").box(10, 10, 10).rotate((0, 0, 0), (1, 0, 0), 90)
    cq.exporters.export(box, str(out))

    mesh = trimesh.load_mesh(str(out))
    assert mesh.is_watertight


def test_heat_set_boss_uses_insert_hole():
    """The lazy hardware path still loads the extension and bores the insert hole."""
    pytest.importorskip("cq_warehouse")
    from blocks import heat_set_boss

    boss = heat_set_boss(size="M3-0.5-6", d_outer=8, h=8)
    assert boss.val().isValid()
    assert Shape.copy.__module__ == "cadquery.occ_impl.shapes"
