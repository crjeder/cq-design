"""Tests for the print-orientation optimizer (trimesh + numpy, no CadQuery)."""

import numpy as np
import trimesh

from print_orientation import (
    _rotation_to_bed,
    _select,
    _strength_score,
    _support_metrics,
    optimize_orientation,
)


def test_in_plane_load_scores_higher_than_across_layers():
    # Identity keeps an X-load in the layer plane; aligning X to build Z puts the
    # load across layers (the FDM-weak direction).
    in_plane = _strength_score(np.eye(4), np.array([1.0, 0.0, 0.0]))
    across = _strength_score(
        trimesh.geometry.align_vectors([1.0, 0.0, 0.0], [0.0, 0.0, 1.0]),
        np.array([1.0, 0.0, 0.0]),
    )
    assert in_plane > across
    assert in_plane == 1.0
    assert across == 0.0


def test_long_bar_with_axial_load_is_laid_flat():
    # A slender bar loaded along its long (X) axis must be oriented so that axis
    # stays in-plane (strength ~1), not stood on end.
    bar = trimesh.creation.box([40.0, 8.0, 8.0])
    result = optimize_orientation(bar, overhang_deg=45.0, load_dir=[1.0, 0.0, 0.0])
    assert result["strength_score"] > 0.9


def test_support_increases_with_exposed_overhang():
    # A cylinder standing on its flat end has no side overhang; lying on its side
    # exposes the whole curved underside as overhang.
    cyl = trimesh.creation.cylinder(radius=10.0, height=40.0)  # axis along Z
    standing, _ = _support_metrics(cyl, np.eye(4), 45.0)
    on_side, _ = _support_metrics(
        cyl, trimesh.geometry.align_vectors([0.0, 0.0, 1.0], [1.0, 0.0, 0.0]), 45.0
    )
    assert on_side > standing


def test_strength_wins_outside_band():
    # Higher strength but more support vs. lower strength with no support: the
    # strong one wins because the gap exceeds the band.
    candidates = [
        {"idx": 0, "strength": 0.95, "support": 100.0, "bed_contact": 5.0},
        {"idx": 1, "strength": 0.40, "support": 0.0, "bed_contact": 50.0},
    ]
    assert _select(candidates, strength_band=0.02)["idx"] == 0


def test_support_breaks_a_strength_tie():
    # Two candidates within the band are tied on strength; least support wins.
    candidates = [
        {"idx": 0, "strength": 0.99, "support": 80.0, "bed_contact": 10.0},
        {"idx": 1, "strength": 0.98, "support": 12.0, "bed_contact": 10.0},
    ]
    assert _select(candidates, strength_band=0.02)["idx"] == 1


def test_inferred_load_is_reported_when_undeclared():
    bar = trimesh.creation.box([40.0, 8.0, 8.0])
    result = optimize_orientation(bar, overhang_deg=45.0)
    assert result["load_inferred"] is True
    # Longest axis is X -> inferred load points along X.
    assert abs(result["load_dir"][0]) == 1.0


def test_deterministic_on_identical_input():
    box = trimesh.creation.box([30.0, 20.0, 10.0])
    a = optimize_orientation(box, overhang_deg=45.0, load_dir=[1.0, 0.0, 0.0])
    b = optimize_orientation(box, overhang_deg=45.0, load_dir=[1.0, 0.0, 0.0])
    assert a == b


def test_rotation_to_bed_lays_face_down():
    # The chosen normal must map to -Z.
    rot = _rotation_to_bed(np.array([0.0, 1.0, 0.0]))
    mapped = rot[:3, :3] @ np.array([0.0, 1.0, 0.0])
    assert np.allclose(mapped, [0.0, 0.0, -1.0], atol=1e-6)
