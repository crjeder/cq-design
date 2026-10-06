# mypy: ignore-errors
# type: ignore  # CAD/trimesh stub-union noise; tests are ruff-linted, not type-checked
"""Tests for the shared placement helper (trimesh side; no CadQuery)."""

import numpy as np

from placement import apply_cq, apply_matrix, to_matrix, transform_direction, transform_point


def test_identity_when_empty():
    assert np.allclose(to_matrix(None), np.eye(4))
    assert np.allclose(to_matrix({}), np.eye(4))


def test_rotate_then_translate():
    # Rotate +90 deg about X maps +Y -> +Z, then translate +5 in Z.
    m = to_matrix({"rotate": [{"axis": "X", "angle_deg": 90}], "translate_mm": [0, 0, 5]})
    p = m @ np.array([0, 1, 0, 1.0])
    assert np.allclose(p[:3], [0, 0, 6], atol=1e-9)


def test_rotation_order_matters():
    # X then Z differs from Z then X.
    xz = to_matrix({"rotate": [{"axis": "X", "angle_deg": 90}, {"axis": "Z", "angle_deg": 90}]})
    zx = to_matrix({"rotate": [{"axis": "Z", "angle_deg": 90}, {"axis": "X", "angle_deg": 90}]})
    assert not np.allclose(xz, zx)


def test_numpy_free_transform_agrees_with_to_matrix():
    # The pure-Python transform helpers (used by plan_validate) must match to_matrix
    # on a non-trivial placement (multiple rotations + translation).
    placement = {
        "rotate": [{"axis": "X", "angle_deg": 90}, {"axis": "Z", "angle_deg": 45}],
        "translate_mm": [3, -2, 5],
    }
    m = to_matrix(placement)
    for vec in ([0, 1, 0], [1, 0, 0], [0.3, -0.7, 0.5]):
        # direction: rotation only (homogeneous w=0)
        expected_dir = (m @ np.array([*vec, 0.0]))[:3]
        assert np.allclose(transform_direction(vec, placement), expected_dir, atol=1e-9)
        # point: rotation then translation (homogeneous w=1)
        expected_pt = (m @ np.array([*vec, 1.0]))[:3]
        assert np.allclose(transform_point(vec, placement), expected_pt, atol=1e-9)


def test_apply_cq_identity_returns_workplane_unchanged():
    import cadquery as cq

    wp = cq.Workplane("XY").box(1, 1, 1)
    assert apply_cq(wp, None) is wp
    assert apply_cq(wp, {}) is wp


def test_apply_cq_matches_to_matrix_convention():
    """apply_cq composes T * R_n * ... * R_1, identical to to_matrix."""
    import cadquery as cq

    placement = {
        "rotate": [{"axis": "X", "angle_deg": 90}, {"axis": "Z", "angle_deg": 45}],
        "translate_mm": [1, 2, 3],
    }
    # Asymmetric solid offset from the origin so rotation order is observable.
    wp = cq.Workplane("XY").box(10, 4, 2).translate((5, 0, 0))
    center0 = np.array(wp.val().Center().toTuple())

    moved = apply_cq(wp, placement)
    center1 = np.array(moved.val().Center().toTuple())

    expected = (to_matrix(placement) @ np.append(center0, 1.0))[:3]
    assert np.allclose(center1, expected, atol=1e-6)


def test_apply_cq_does_not_deepcopy_with_patch_active(tmp_path):
    """With cq_warehouse's Shape patch active, apply_cq must not enter Shape.copy."""
    import cadquery as cq
    import cq_warehouse.extensions  # noqa: F401 -- activate the global Shape patch
    from cadquery.occ_impl.shapes import Shape

    wp = cq.Workplane("XY").box(10, 10, 4)
    placement = {"rotate": [{"axis": "X", "angle_deg": 90}], "translate_mm": [0, 0, 5]}

    orig_copy = Shape.copy

    def tripwire(self, *args, **kwargs):
        raise AssertionError("apply_cq entered Shape.copy (deepcopy/BinTools path)")

    Shape.copy = tripwire
    try:
        moved = apply_cq(wp, placement)
    finally:
        Shape.copy = orig_copy

    out = tmp_path / "moved.stl"
    cq.exporters.export(moved, str(out))
    assert out.exists() and out.stat().st_size > 0


def test_apply_matrix_matches_apply_cq():
    """apply_matrix(to_matrix(p)) positions a solid identically to apply_cq(p)."""
    import cadquery as cq

    placement = {
        "rotate": [{"axis": "X", "angle_deg": 90}, {"axis": "Z", "angle_deg": 45}],
        "translate_mm": [1, 2, 3],
    }
    wp = cq.Workplane("XY").box(10, 4, 2).translate((5, 0, 0))
    a = apply_cq(wp, placement).val()
    b = apply_matrix(wp, to_matrix(placement)).val()
    assert np.allclose(a.Center().toTuple(), b.Center().toTuple(), atol=1e-6)
    assert np.allclose(a.BoundingBox().xlen, b.BoundingBox().xlen, atol=1e-6)
    assert np.allclose(a.BoundingBox().zlen, b.BoundingBox().zlen, atol=1e-6)
