"""Tests for the shared placement helper (trimesh side; no CadQuery)."""

import numpy as np

from placement import to_matrix


def test_identity_when_empty():
    assert np.allclose(to_matrix(None), np.eye(4))
    assert np.allclose(to_matrix({}), np.eye(4))


def test_rotate_then_translate():
    # Rotate +90 deg about X maps +Y -> +Z, then translate +5 in Z.
    m = to_matrix(
        {"rotate": [{"axis": "X", "angle_deg": 90}], "translate_mm": [0, 0, 5]}
    )
    p = m @ np.array([0, 1, 0, 1.0])
    assert np.allclose(p[:3], [0, 0, 6], atol=1e-9)


def test_rotation_order_matters():
    # X then Z differs from Z then X.
    xz = to_matrix(
        {"rotate": [{"axis": "X", "angle_deg": 90}, {"axis": "Z", "angle_deg": 90}]}
    )
    zx = to_matrix(
        {"rotate": [{"axis": "Z", "angle_deg": 90}, {"axis": "X", "angle_deg": 90}]}
    )
    assert not np.allclose(xz, zx)
