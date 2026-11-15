# mypy: ignore-errors
# type: ignore  # CAD/trimesh stub-union noise; tests are ruff-linted, not type-checked
"""Tests for the print-orientation optimizer (trimesh + numpy, no CadQuery)."""

import json
import os
import subprocess
import sys

import numpy as np
import pytest
import trimesh

import print_orientation
from freshness import script_hash
from print_orientation import (
    _area_cumulation_normals,
    _gentle_incline_fraction,
    _rotation_to_bed,
    _select,
    _stability_metrics,
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


def test_stability_flat_footprint_is_stable():
    # A box resting flat: full-face contact, center of mass centered over it.
    box = trimesh.creation.box([40.0, 40.0, 10.0])
    assert _stability_metrics(box) is True


def test_stability_edge_balance_is_unstable():
    # Tip the box 45 degrees so it balances on one edge: the contact footprint
    # degenerates to a line (fewer than 3 distinct XY points) -- can't form a
    # resting polygon, so it must be unstable regardless of support cost.
    box = trimesh.creation.box([100.0, 100.0, 10.0])
    tipped = box.copy()
    rot = trimesh.transformations.rotation_matrix(np.radians(45.0), [1.0, 0.0, 0.0])
    tipped.apply_transform(rot)
    assert _stability_metrics(tipped) is False


def test_select_prefers_stable_over_lower_support_unstable_candidate():
    # Regression for the near-point-balance bug: with strength tied (the
    # no-load/compression case), an unstable candidate with near-zero support
    # cost must not beat a stable candidate with a small support cost from a
    # minor feature.
    candidates = [
        {"idx": 0, "strength": 1.0, "support": 3.0, "bed_contact": 1600.0, "stable": True},
        {"idx": 1, "strength": 1.0, "support": 0.0, "bed_contact": 0.0, "stable": False},
    ]
    assert _select(candidates, "strength")["idx"] == 0


def test_select_falls_back_to_full_set_when_all_unstable():
    # No flat resting face exists at all: the gate must not eliminate every
    # candidate -- fall back to the full set so a recommendation is still made.
    candidates = [
        {"idx": 0, "strength": 0.9, "support": 5.0, "bed_contact": 10.0, "stable": False},
        {"idx": 1, "strength": 0.5, "support": 1.0, "bed_contact": 40.0, "stable": False},
    ]
    assert _select(candidates, "strength")["idx"] == 0


def test_optimize_orientation_reports_stable_and_no_exclusion_for_plain_box():
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    result = optimize_orientation(box, overhang_deg=45.0)
    assert result["stable"] is True
    assert "excluded" not in result["rationale"]


_PRINT_ORIENTATION_CLI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "print_orientation.py"
)


def test_cli_source_script_stamps_result(tmp_path):
    stl = tmp_path / "box.stl"
    trimesh.creation.box([20.0, 20.0, 4.0]).export(str(stl))
    script = tmp_path / "part.py"
    script.write_text("result = 1\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, _PRINT_ORIENTATION_CLI, str(stl), "--source-script", str(script)],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["source_script_hash"] == script_hash(str(script))


def test_cli_without_source_script_is_unstamped(tmp_path):
    stl = tmp_path / "box.stl"
    trimesh.creation.box([20.0, 20.0, 4.0]).export(str(stl))

    proc = subprocess.run(
        [sys.executable, _PRINT_ORIENTATION_CLI, str(stl)],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert "source_script_hash" not in result


def _bridge_slab(gap):
    """Base + two pillars + slab: a `gap` mm bridge in the authored pose."""
    box = trimesh.creation.box
    parts = []
    for size, at in (
        ([60.0, 20.0, 2.0], [30.0, 10.0, 1.0]),
        ([10.0, 20.0, 10.0], [5.0, 10.0, 7.0]),
        ([10.0, 20.0, 10.0], [15.0 + gap, 10.0, 7.0]),
        ([20.0 + gap, 20.0, 2.0], [(20.0 + gap) / 2, 10.0, 13.0]),
    ):
        b = box(size)
        b.apply_translation(at)
        parts.append(b)
    return trimesh.boolean.union(parts, engine="manifold")


def test_short_bridge_costs_far_less_than_long_span():
    short, _ = _support_metrics(_bridge_slab(6.0), 45.0)
    long_, _ = _support_metrics(_bridge_slab(25.0), 45.0)
    assert short < 0.15 * long_
    assert _support_metrics(_bridge_slab(25.0), 45.0, bridge_max_mm=30.0)[0] < 0.15 * long_


def test_optimize_orientation_is_deterministic():
    mesh = _bridge_slab(6.0)
    a = optimize_orientation(mesh, 45.0)
    b = optimize_orientation(mesh.copy(), 45.0)
    assert a["rotate"] == b["rotate"]
    assert a["support_score"] == b["support_score"]


def _fem_stress_result(normal_to_fi_p99: dict) -> dict:
    """A minimal fem_check.py-shaped result: status ok, one candidate per normal with
    the given fi_p99 (fi_max set equal -- not used by the orientation lookup)."""
    return {
        "status": "ok",
        "candidates": [
            {"normal": list(normal), "fi_max": fi, "fi_p99": fi}
            for normal, fi in normal_to_fi_p99.items()
        ],
    }


def test_fem_stress_overrides_strength_for_matching_candidate():
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    # box(0,0,1) is the lowest-cost bed-down face by support (flat top/bottom); making
    # its fi_p99 the worst (0.9) and every other axis normal the best (0.05) should flip
    # the strength winner away from it relative to the neutral (no fem_stress) case.
    fem_stress = _fem_stress_result(
        {
            (1.0, 0.0, 0.0): 0.05,
            (-1.0, 0.0, 0.0): 0.05,
            (0.0, 1.0, 0.0): 0.05,
            (0.0, -1.0, 0.0): 0.05,
            (0.0, 0.0, 1.0): 0.9,
            (0.0, 0.0, -1.0): 0.9,
        }
    )
    result = optimize_orientation(box, overhang_deg=45.0, fem_stress=fem_stress)
    assert result["strength_source"] == "fem"
    assert result["strength_score"] == pytest.approx(0.95)
    assert "FEM failure index" in result["rationale"]


def test_fem_stress_skipped_result_is_byte_identical_to_absent_flag():
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    without_flag = optimize_orientation(box, overhang_deg=45.0, load_dir=[1.0, 0.0, 0.0])
    with_skipped = optimize_orientation(
        box, overhang_deg=45.0, load_dir=[1.0, 0.0, 0.0], fem_stress={"status": "skipped"}
    )
    assert without_flag == with_skipped
    assert with_skipped["strength_source"] == "declared_load"


def test_fem_stress_no_matching_candidates_falls_back_to_declared_load():
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    # An oblique normal far outside every axis-aligned candidate's merge tolerance.
    fem_stress = _fem_stress_result({(1.0, 1.0, 1.0): 0.01})
    without_flag = optimize_orientation(box, overhang_deg=45.0, load_dir=[1.0, 0.0, 0.0])
    with_unmatched = optimize_orientation(
        box, overhang_deg=45.0, load_dir=[1.0, 0.0, 0.0], fem_stress=fem_stress
    )
    assert without_flag == with_unmatched
    assert with_unmatched["strength_source"] == "declared_load"


def test_fem_stress_absent_reports_neutral_source_without_load():
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    result = optimize_orientation(box, overhang_deg=45.0)
    assert result["strength_source"] == "neutral"


def test_cli_fem_stress_flag(tmp_path):
    stl = tmp_path / "box.stl"
    trimesh.creation.box([40.0, 20.0, 6.0]).export(str(stl))
    fem_stress_path = tmp_path / "fem_stress.json"
    fem_stress_path.write_text(
        json.dumps(
            _fem_stress_result(
                {
                    (1.0, 0.0, 0.0): 0.05,
                    (-1.0, 0.0, 0.0): 0.05,
                    (0.0, 1.0, 0.0): 0.05,
                    (0.0, -1.0, 0.0): 0.05,
                    (0.0, 0.0, 1.0): 0.9,
                    (0.0, 0.0, -1.0): 0.9,
                }
            )
        ),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, _PRINT_ORIENTATION_CLI, str(stl), "--fem-stress", str(fem_stress_path)],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["strength_source"] == "fem"


def _speed_model_result(normal_to_speed: dict) -> dict:
    """A minimal toolpath_speed.py --emit-candidates-shaped result: status ok, one
    candidate per normal with the given (total_time_s, speed_efficiency, stalled)."""
    return {
        "status": "ok",
        "candidates": [
            {
                "normal": list(normal),
                "status": "ok",
                "total_time_s": t,
                "speed_efficiency": eff,
                "stalled": stalled,
            }
            for normal, (t, eff, stalled) in normal_to_speed.items()
        ],
    }


def test_min_print_time_selects_least_estimated_time():
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    speed_model = _speed_model_result(
        {
            (1.0, 0.0, 0.0): (500.0, 0.5, False),
            (-1.0, 0.0, 0.0): (500.0, 0.5, False),
            (0.0, 1.0, 0.0): (500.0, 0.5, False),
            (0.0, -1.0, 0.0): (500.0, 0.5, False),
            (0.0, 0.0, 1.0): (50.0, 0.9, False),
            (0.0, 0.0, -1.0): (50.0, 0.9, False),
        }
    )
    result = optimize_orientation(
        box, overhang_deg=45.0, optimize_for="min_print_time", speed_model=speed_model
    )
    assert result["total_time_s"] == pytest.approx(50.0)
    assert result["speed_efficiency"] == pytest.approx(0.9)
    assert result["stalled"] is False


def test_min_print_time_without_speed_model_falls_back_to_build_height():
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    with_time_mode = optimize_orientation(box, overhang_deg=45.0, optimize_for="min_print_time")
    with_height_mode = optimize_orientation(box, overhang_deg=45.0, optimize_for="min_build_height")
    assert with_time_mode["rotate"] == with_height_mode["rotate"]
    assert "total_time_s" not in with_time_mode


def test_speed_model_absent_result_is_byte_identical_to_no_flag():
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    without_flag = optimize_orientation(box, overhang_deg=45.0, load_dir=[1.0, 0.0, 0.0])
    with_skipped = optimize_orientation(
        box, overhang_deg=45.0, load_dir=[1.0, 0.0, 0.0], speed_model={"status": "skipped"}
    )
    assert without_flag == with_skipped
    assert "total_time_s" not in with_skipped


def test_speed_model_fields_present_only_when_matched():
    box = trimesh.creation.box([40.0, 20.0, 6.0])
    speed_model = _speed_model_result({(0.0, 0.0, 1.0): (50.0, 0.9, False)})
    result = optimize_orientation(box, overhang_deg=45.0, speed_model=speed_model)
    # Default (strength) mode may or may not land on the one candidate with speed data;
    # either way, when present the fields agree with that candidate's values.
    if "total_time_s" in result:
        assert result["total_time_s"] == pytest.approx(50.0)
        assert result["speed_efficiency"] == pytest.approx(0.9)
    else:
        assert "speed_efficiency" not in result and "stalled" not in result


def test_shared_bed_mask_leaves_metrics_unchanged():
    cone = trimesh.creation.cone(radius=10.0, height=15.0)
    cone.apply_transform(trimesh.transformations.rotation_matrix(0.4, [1.0, 0.3, 0.0]))
    cone.apply_translation([0.0, 0.0, -cone.bounds[0][2]])
    mask = print_orientation.bed_contact_mask(cone)
    assert _support_metrics(cone, 45.0) == _support_metrics(cone, 45.0, contact_mask=mask)
    assert _gentle_incline_fraction(cone) == _gentle_incline_fraction(cone, mask)
    assert _stability_metrics(cone) == _stability_metrics(cone, contact_mask=mask)


def test_optimize_orientation_evaluates_bed_mask_once_per_pose(monkeypatch):
    calls = [0]
    real = print_orientation.bed_mask_from

    def counted(*args):
        calls[0] += 1
        return real(*args)

    monkeypatch.setattr(print_orientation, "bed_mask_from", counted)
    box = trimesh.creation.box([30.0, 20.0, 10.0])
    optimize_orientation(box, overhang_deg=45.0)
    assert calls[0] == len(enumerate_candidate_normals(box))


def test_base_face_areas_equal_posed_face_areas():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    mesh.apply_scale([1.0, 2.0, 3.0])
    rotation = _rotation_to_bed(np.array([0.3, -0.5, 0.8]) / np.linalg.norm([0.3, -0.5, 0.8]))
    posed = mesh.copy()
    posed.apply_transform(rotation)
    fresh = trimesh.Trimesh(posed.vertices, posed.faces, process=False).area_faces
    assert np.allclose(mesh.area_faces, fresh)


def _equivalence_meshes():
    cone = trimesh.creation.cone(radius=10.0, height=25.0)
    cyl = trimesh.creation.cylinder(radius=8.0, height=30.0, sections=24)
    ball = trimesh.creation.icosphere(subdivisions=2)
    ball.apply_scale([10.0, 14.0, 20.0])
    tee = trimesh.util.concatenate(
        [
            trimesh.creation.box([40.0, 10.0, 6.0]),
            trimesh.creation.box([8.0, 8.0, 30.0]).apply_translation([0.0, 0.0, 18.0]),
        ]
    )
    slab = trimesh.creation.box([60.0, 40.0, 5.0])
    return {"cone": cone, "cylinder": cyl, "ellipsoid": ball, "tee": tee, "slab": slab}


@pytest.mark.parametrize("mode", print_orientation.OPTIMIZE_MODES)
@pytest.mark.parametrize("name", ["cone", "cylinder", "ellipsoid", "tee", "slab"])
@pytest.mark.parametrize("load", [None, [1.0, 0.0, 0.0]])
def test_pruned_search_equals_exhaustive(name, mode, load):
    mesh = _equivalence_meshes()[name]
    kwargs = {"overhang_deg": 45.0, "load_dir": load, "optimize_for": mode}
    full = optimize_orientation(mesh, prune=False, **kwargs)
    fast = optimize_orientation(mesh, prune=True, **kwargs)
    assert fast == full


def test_pruning_scores_fewer_candidates_exactly(monkeypatch):
    calls = {"n": 0}
    real = print_orientation._support_metrics

    def counted(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(print_orientation, "_support_metrics", counted)
    cyl = trimesh.creation.cylinder(radius=8.0, height=30.0, sections=48)
    optimize_orientation(cyl, overhang_deg=45.0, optimize_for="min_support", prune=True)
    pruned = calls["n"]
    calls["n"] = 0
    optimize_orientation(cyl, overhang_deg=45.0, optimize_for="min_support", prune=False)
    assert pruned < calls["n"] == len(enumerate_candidate_normals(cyl))


def test_prune_lower_bound_never_exceeds_exact_support():
    mesh = _equivalence_meshes()["tee"]
    base = mesh.copy()
    hull = np.asarray(mesh.convex_hull.vertices)
    for normal in enumerate_candidate_normals(mesh):
        rotation = _rotation_to_bed(normal)
        nz, _, bed, _ = print_orientation._pose_arrays(
            rotation, np.asarray(base.face_normals), np.asarray(base.triangles_center), hull
        )
        raw = print_orientation._raw_support_cost(nz, np.asarray(base.area_faces), bed, 45.0)
        posed = base.copy()
        posed.apply_transform(rotation)
        exact, _ = _support_metrics(posed, 45.0)
        lb = print_orientation.BRIDGE_COST_FACTOR * raw - print_orientation.SUPPORT_ROUNDING_SLACK
        assert lb <= exact <= raw + print_orientation.SUPPORT_ROUNDING_SLACK


def test_progress_lines_reported_with_callback(monkeypatch):
    monkeypatch.setattr(print_orientation, "PROGRESS_INTERVAL_S", 0.0)
    lines = []
    cyl = trimesh.creation.cylinder(radius=8.0, height=30.0, sections=48)
    optimize_orientation(cyl, overhang_deg=45.0, progress=lines.append)
    assert lines
    assert any("scan candidate" in line for line in lines)
    assert all("elapsed" in line and "left" in line for line in lines)


def test_no_progress_callback_prints_nothing(capsys):
    optimize_orientation(trimesh.creation.box([20.0, 20.0, 20.0]), overhang_deg=45.0)
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_pose_arrays_match_posed_mesh():
    mesh = _equivalence_meshes()["ellipsoid"]
    hull = np.asarray(mesh.convex_hull.vertices)
    for normal in enumerate_candidate_normals(mesh):
        rotation = _rotation_to_bed(normal)
        nz, cz, bed, height = print_orientation._pose_arrays(
            rotation, np.asarray(mesh.face_normals), np.asarray(mesh.triangles_center), hull
        )
        posed = mesh.copy()
        posed.apply_transform(rotation)
        assert np.allclose(nz, posed.face_normals[:, 2])
        assert np.allclose(cz, posed.triangles_center[:, 2])
        assert np.array_equal(bed, print_orientation.bed_contact_mask(posed))
        assert height == round(float(posed.extents[2]), 3)


def _fake(idx, lb, support, bed_contact=1.0, stable=True):
    return {
        "idx": idx,
        "support_lb": lb,
        "true_support": support,
        "strength": 1.0,
        "bed_contact": bed_contact,
        "stable": stable,
    }


def test_candidate_whose_bound_equals_incumbent_is_still_scored():
    # Both candidates cost exactly 10; the second has the larger bed contact, so it must
    # win the tiebreak -- which only happens if its lower bound (10, not above the
    # incumbent's 10) does not get it pruned.
    cands = [_fake(0, 10.0, 10.0, bed_contact=1.0), _fake(1, 10.0, 10.0, bed_contact=5.0)]
    scored_ids = []

    def score(c):
        c["support"] = c["true_support"]
        scored_ids.append(c["idx"])

    scored = print_orientation._search_support(cands, "strength", 0.02, True, score)
    assert scored_ids == [0, 1]
    assert _select(scored, "strength")["idx"] == 1


def test_candidate_with_bound_above_incumbent_is_skipped():
    cands = [_fake(0, 1.0, 5.0), _fake(1, 6.0, 9.0), _fake(2, 5.0, 5.0)]
    scored_ids = []

    def score(c):
        c["support"] = c["true_support"]
        scored_ids.append(c["idx"])

    print_orientation._search_support(cands, "strength", 0.02, True, score)
    assert scored_ids == [0, 2]  # idx 1: lower bound 6 > best exact 5


def test_min_support_scores_candidates_inside_the_support_band():
    cands = [_fake(0, 0.0, 3.0), _fake(1, 3.5, 3.5), _fake(2, 4.5, 9.0)]
    scored_ids = []

    def score(c):
        c["support"] = c["true_support"]
        scored_ids.append(c["idx"])

    print_orientation._search_support(cands, "min_support", 0.02, True, score)
    assert scored_ids == [0, 1]  # bound 4.5 > best 3.0 + SUPPORT_BAND
