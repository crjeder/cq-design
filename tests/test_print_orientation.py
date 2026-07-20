# mypy: ignore-errors
# type: ignore  # CAD/trimesh stub-union noise; tests are ruff-linted, not type-checked
"""Tests for the print-orientation optimizer (trimesh + numpy, no CadQuery)."""

import numpy as np
import pytest
import trimesh

from print_orientation import (
    _area_cumulation_normals,
    _gentle_incline_fraction,
    _rotation_to_bed,
    _select,
    _strength_score,
    _support_metrics,
    _visual_metrics,
    enumerate_candidate_normals,
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


def test_compression_load_is_orientation_neutral_regardless_of_axis():
    # Compression doesn't stress the interlayer bond, so strength score is always
    # 1.0 no matter how the load direction sits relative to the layers.
    in_plane = _strength_score(np.eye(4), np.array([1.0, 0.0, 0.0]), load_type="compression")
    across = _strength_score(
        trimesh.geometry.align_vectors([1.0, 0.0, 0.0], [0.0, 0.0, 1.0]),
        np.array([1.0, 0.0, 0.0]),
        load_type="compression",
    )
    assert in_plane == 1.0
    assert across == 1.0


def test_flat_wide_part_under_compression_keeps_flat_orientation():
    # Regression for the TV-pedestal bug: a flat, wide part loaded in pure
    # compression along Z (a resting weight pressing straight down) must NOT be
    # tipped onto its edge to chase layer-plane "strength". Under tension-style
    # scoring, the flat-down pose scores worst (load stays along Z) and any
    # edge-standing pose scores near 1.0 with no support-cost penalty (a plain box
    # has no overhangs either way) -- so "strength" mode picks an edge-standing
    # pose, ~10x taller than necessary. With load_type=compression, strength is
    # neutral for every pose and support/bed-contact keep it flat.
    slab = trimesh.creation.box([100.0, 100.0, 10.0])
    tension_result = optimize_orientation(
        slab, overhang_deg=45.0, load_dir=[0.0, 0.0, 1.0], load_type="tension"
    )
    compression_result = optimize_orientation(
        slab, overhang_deg=45.0, load_dir=[0.0, 0.0, 1.0], load_type="compression"
    )
    # Tension-style scoring tips the slab onto its 100 mm edge: confirms the bug
    # reproduces under the old default.
    assert tension_result["build_height_mm"] > 50.0
    # Compression scoring keeps it flat: build height stays at the part's thin
    # (10 mm) dimension.
    assert compression_result["strength_score"] == 1.0
    assert compression_result["build_height_mm"] < 20.0
    assert compression_result["load_type"] == "compression"


def test_load_type_defaults_to_tension():
    box = trimesh.creation.box([20.0, 20.0, 20.0])
    result = optimize_orientation(box, overhang_deg=45.0, load_dir=[1.0, 0.0, 0.0])
    assert result["load_type"] == "tension"


def test_unknown_load_type_rejected():
    import pytest

    box = trimesh.creation.box([20.0, 20.0, 20.0])
    with pytest.raises(ValueError, match="load_type"):
        optimize_orientation(box, overhang_deg=45.0, load_type="squash")


def test_support_increases_with_exposed_overhang():
    # A cylinder standing on its flat end has no side overhang; lying on its side
    # exposes the whole curved underside as overhang.
    cyl = trimesh.creation.cylinder(radius=10.0, height=40.0)  # axis along Z
    standing, _ = _support_metrics(cyl, 45.0)
    cyl_on_side = cyl.copy()
    cyl_on_side.apply_transform(trimesh.geometry.align_vectors([0.0, 0.0, 1.0], [1.0, 0.0, 0.0]))
    on_side, _ = _support_metrics(cyl_on_side, 45.0)
    assert on_side > standing


@pytest.mark.parametrize(
    "candidates, mode, expected_idx",
    [
        pytest.param(
            [
                {"idx": 0, "strength": 0.95, "support": 100.0, "bed_contact": 5.0},
                {"idx": 1, "strength": 0.40, "support": 0.0, "bed_contact": 50.0},
            ],
            "strength",
            0,
            id="strength_wins_outside_band",
            # Higher strength but more support vs. lower strength with no support: the
            # strong one wins because the gap exceeds the band.
        ),
        pytest.param(
            [
                {"idx": 0, "strength": 0.99, "support": 80.0, "bed_contact": 10.0},
                {"idx": 1, "strength": 0.98, "support": 12.0, "bed_contact": 10.0},
            ],
            "strength",
            1,
            id="support_breaks_a_strength_tie",
            # Two candidates within the band are tied on strength; least support wins.
        ),
        pytest.param(
            [
                {"idx": 0, "strength": 0.95, "support": 100.0, "bed_contact": 5.0, "visual": 0.1},
                {"idx": 1, "strength": 0.40, "support": 2.0, "bed_contact": 50.0, "visual": 0.2},
            ],
            "min_support",
            1,
            id="min_support_mode_minimizes_support",
            # Strongest candidate has heavy support; min_support picks the low-support one
            # even though it is much weaker (outside any strength consideration).
        ),
        pytest.param(
            [
                {"idx": 0, "strength": 0.50, "support": 5.0, "bed_contact": 10.0, "visual": 0.1},
                {"idx": 1, "strength": 0.90, "support": 5.5, "bed_contact": 10.0, "visual": 0.1},
            ],
            "min_support",
            1,
            id="min_support_strength_breaks_a_support_tie",
            # Two candidates within the support band; best strength wins the tie.
        ),
        pytest.param(
            [
                {"idx": 0, "strength": 0.95, "support": 0.0, "bed_contact": 5.0, "visual": 0.1},
                {"idx": 1, "strength": 0.40, "support": 50.0, "bed_contact": 5.0, "visual": 0.9},
            ],
            "visual_quality",
            1,
            id="visual_mode_picks_best_visual",
            # Best visual wins over a stronger, lower-support candidate.
        ),
    ],
)
def test_select_picks_expected_candidate(candidates, mode, expected_idx):
    assert _select(candidates, mode)["idx"] == expected_idx


def test_unknown_mode_rejected():
    import pytest

    box = trimesh.creation.box([10.0, 10.0, 10.0])
    with pytest.raises(ValueError):
        optimize_orientation(box, overhang_deg=45.0, optimize_for="speed")


def test_modes_can_select_different_orientations():
    # An L-shaped part: the three modes are free to disagree; each result must at
    # least report the mode it ran under and be internally consistent.
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    strength = optimize_orientation(box, overhang_deg=45.0, optimize_for="strength")
    min_support = optimize_orientation(box, overhang_deg=45.0, optimize_for="min_support")
    visual = optimize_orientation(box, overhang_deg=45.0, optimize_for="visual_quality")
    assert strength["optimize_for"] == "strength"
    assert min_support["optimize_for"] == "min_support"
    assert visual["optimize_for"] == "visual_quality"


def test_cosmetic_face_down_scores_higher_than_up():
    # A flat plate: orienting its +Z face toward the bed should beat leaving it up.
    plate = trimesh.creation.box([40.0, 40.0, 4.0])
    show = np.array([0.0, 0.0, 1.0])
    down_rot = trimesh.geometry.align_vectors([0.0, 0.0, 1.0], [0.0, 0.0, -1.0])
    plate_down = plate.copy()
    plate_down.apply_transform(down_rot)
    visual_up, cos_up, _ = _visual_metrics(plate, np.eye(4), show)
    visual_down, cos_down, _ = _visual_metrics(plate_down, down_rot, show)
    assert cos_down > cos_up
    assert visual_down > visual_up


def test_more_gentle_incline_area_lowers_visual_score():
    # A flat box has no gentle inclines; a cone's slanted wall does.
    box = trimesh.creation.box([20.0, 20.0, 20.0])
    cone = trimesh.creation.cone(radius=20.0, height=10.0)  # ~27 deg wall: gentle
    box_frac = _gentle_incline_fraction(box)
    cone_frac = _gentle_incline_fraction(cone)
    assert cone_frac > box_frac


def test_show_face_inferred_flag():
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    inferred = optimize_orientation(box, overhang_deg=45.0, optimize_for="visual_quality")
    declared = optimize_orientation(
        box, overhang_deg=45.0, optimize_for="visual_quality", show_face=[0.0, 0.0, 1.0]
    )
    assert inferred["show_face_inferred"] is True
    assert declared["show_face_inferred"] is False


def test_visual_mode_deterministic():
    cone = trimesh.creation.cone(radius=15.0, height=20.0)
    a = optimize_orientation(cone, overhang_deg=45.0, optimize_for="visual_quality")
    b = optimize_orientation(cone, overhang_deg=45.0, optimize_for="visual_quality")
    assert a == b


def test_undeclared_load_is_neutral_not_guessed():
    # No load declared: the optimizer must NOT guess a load axis from geometry.
    # Strength is neutral (1.0 for every candidate), load_dir is null, and the
    # result flags that no load was declared.
    bar = trimesh.creation.box([40.0, 8.0, 8.0])
    result = optimize_orientation(bar, overhang_deg=45.0)
    assert result["load_declared"] is False
    assert result["load_dir"] is None
    assert result["strength_score"] == 1.0
    assert "no load declared" in result["rationale"]


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


def test_area_cumulation_surfaces_dominant_face():
    # The two big faces of a thin slab dominate by area; tilt it off-axis so the
    # axis baseline can't trivially supply the direction. Area cumulation must
    # surface a direction aligned with the (rotated) large face normal.
    slab = trimesh.creation.box([40.0, 40.0, 3.0])
    rot = trimesh.transformations.rotation_matrix(np.radians(20.0), [1.0, 0.0, 0.0])
    slab.apply_transform(rot)
    expected = rot[:3, :3] @ np.array([0.0, 0.0, 1.0])
    tops = _area_cumulation_normals(slab)
    assert any(abs(float(np.dot(t, expected))) > 0.99 for t in tops)


def test_candidate_set_bounded_after_dedup():
    # Hull facets + 6 axes + area-cumulation all collapse to the box's 6 unique
    # face normals after the merge pass.
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    assert len(enumerate_candidate_normals(box)) == 6


def test_near_coplanar_resting_face_counts_as_bed_contact():
    # A wide downward face dipping 0.3 mm at one corner: its centroid sits 0.2 mm
    # above the lowest point -- inside the first-layer band, outside the old tight
    # epsilon -- so it must count as bed contact.
    verts = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, -0.3]])
    mesh = trimesh.Trimesh(vertices=verts, faces=[[0, 2, 1]], process=False)
    assert mesh.face_normals[0][2] < -0.5  # downward-facing
    _, bed_contact = _support_metrics(mesh, 45.0)
    assert bed_contact > 0.0


def test_min_build_height_selects_smallest_extent():
    candidates = [
        {
            "idx": 0,
            "strength": 0.9,
            "support": 0.0,
            "bed_contact": 5.0,
            "visual": 0.1,
            "build_height": 40.0,
        },
        {
            "idx": 1,
            "strength": 0.5,
            "support": 0.0,
            "bed_contact": 5.0,
            "visual": 0.1,
            "build_height": 10.0,
        },
    ]
    assert _select(candidates, "min_build_height")["idx"] == 1


def test_min_build_height_picks_lowest_profile():
    # A long bar must be laid down (height ~10), not stood on end (height ~40).
    bar = trimesh.creation.box([40.0, 10.0, 10.0])
    result = optimize_orientation(bar, overhang_deg=45.0, optimize_for="min_build_height")
    assert result["optimize_for"] == "min_build_height"
    assert result["build_height_mm"] <= 10.0 + 1e-3


def test_min_build_height_deterministic():
    bar = trimesh.creation.box([40.0, 10.0, 10.0])
    a = optimize_orientation(bar, overhang_deg=45.0, optimize_for="min_build_height")
    b = optimize_orientation(bar, overhang_deg=45.0, optimize_for="min_build_height")
    assert a == b
