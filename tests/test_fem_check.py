"""Tests for src/fem_check.py.

Skip-path tests (missing load case fields, unknown material, an anchor naming a
missing/incomplete interface, and a simulated missing dependency) run without the
optional `fem` group. Solve-path tests need real geometry solved by gmsh/scikit-fem and
are individually marked `@_needs_fem` (not a module-level `importorskip`, which would
skip collection of the whole module -- including the skip-path tests above that need no
gmsh/skfem at all) so they alone skip when the `fem` group is not installed
(`uv sync --group fem`).
"""

import importlib.util
import json
import os
import subprocess
import sys

import cadquery as cq
import numpy as np
import pytest

import fem_check
from fem_check import _resolve_boundary_conditions, failure_index, run_fem_check

FEM_CHECK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "fem_check.py"
)


def _plan(load=None, material="PETG", interfaces=None):
    return {
        "material": material,
        "parts": [
            {
                "id": "bracket",
                "interfaces": interfaces or [],
                **({"load": load} if load is not None else {}),
            }
        ],
    }


# ---- precondition / skip-path tests (no gmsh/skfem needed) ----


def test_missing_load_is_skipped():
    result = run_fem_check("unused.step", _plan(load=None), "bracket", 1.0)
    assert result["status"] == "skipped"
    assert "load" in result["reason"]


def test_missing_magnitude_is_skipped():
    plan = _plan(load={"dir": [0, 0, -1], "applied_at": "a", "grounded_at": ["b"]})
    result = run_fem_check("unused.step", plan, "bracket", 1.0)
    assert result["status"] == "skipped"
    assert "magnitude_n" in result["reason"]


def test_missing_applied_at_is_skipped():
    plan = _plan(load={"dir": [0, 0, -1], "magnitude_n": 1.0, "grounded_at": ["b"]})
    result = run_fem_check("unused.step", plan, "bracket", 1.0)
    assert result["status"] == "skipped"
    assert "applied_at" in result["reason"]


def test_missing_grounded_at_is_skipped():
    plan = _plan(load={"dir": [0, 0, -1], "magnitude_n": 1.0, "applied_at": "a"})
    result = run_fem_check("unused.step", plan, "bracket", 1.0)
    assert result["status"] == "skipped"
    assert "grounded_at" in result["reason"]


def test_applied_at_naming_missing_interface_is_skipped():
    plan = _plan(
        load={
            "dir": [0, 0, -1],
            "magnitude_n": 1.0,
            "applied_at": "nope",
            "grounded_at": ["also_nope"],
        }
    )
    result = run_fem_check("unused.step", plan, "bracket", 1.0)
    assert result["status"] == "skipped"
    assert "nope" in result["reason"]


def test_anchor_without_position_mm_is_skipped():
    plan = _plan(
        load={
            "dir": [0, 0, -1],
            "magnitude_n": 1.0,
            "applied_at": "tip",
            "grounded_at": ["root"],
        },
        interfaces=[
            {"type": "shelf", "name": "tip", "diameter_mm": 5},  # no position_mm
            {"type": "screw_boss", "name": "root", "position_mm": [0, 0, 0], "diameter_mm": 5},
        ],
    )
    result = run_fem_check("unused.step", plan, "bracket", 1.0)
    assert result["status"] == "skipped"
    assert "position_mm" in result["reason"]


def test_anchor_without_diameter_or_size_is_skipped():
    plan = _plan(
        load={
            "dir": [0, 0, -1],
            "magnitude_n": 1.0,
            "applied_at": "tip",
            "grounded_at": ["root"],
        },
        interfaces=[
            {"type": "shelf", "name": "tip", "position_mm": [10, 0, 0]},  # no size
            {"type": "screw_boss", "name": "root", "position_mm": [0, 0, 0], "diameter_mm": 5},
        ],
    )
    result = run_fem_check("unused.step", plan, "bracket", 1.0)
    assert result["status"] == "skipped"
    assert "footprint" in result["reason"] or "diameter_mm" in result["reason"]


def test_unknown_material_is_skipped():
    plan = _plan(
        load={
            "dir": [0, 0, -1],
            "magnitude_n": 1.0,
            "applied_at": "tip",
            "grounded_at": ["root"],
        },
        material="Unobtainium",
        interfaces=[
            {"type": "shelf", "name": "tip", "position_mm": [10, 0, 0], "diameter_mm": 5},
            {"type": "screw_boss", "name": "root", "position_mm": [0, 0, 0], "diameter_mm": 5},
        ],
    )
    result = run_fem_check("unused.step", plan, "bracket", 1.0)
    assert result["status"] == "skipped"
    assert "Unobtainium" in result["reason"]


def test_part_not_found_is_skipped():
    plan = _plan(load=None)
    result = run_fem_check("unused.step", plan, "does_not_exist", 1.0)
    assert result["status"] == "skipped"


def test_missing_dependencies_is_skipped(monkeypatch):
    monkeypatch.setattr(
        fem_check,
        "_probe_dependencies",
        lambda: (None, None, "gmsh not installed (optional 'fem' dependency group)"),
    )
    plan = _plan(
        load={
            "dir": [0, 0, -1],
            "magnitude_n": 1.0,
            "applied_at": "tip",
            "grounded_at": ["root"],
        },
        interfaces=[
            {"type": "shelf", "name": "tip", "position_mm": [10, 0, 0], "diameter_mm": 5},
            {"type": "screw_boss", "name": "root", "position_mm": [0, 0, 0], "diameter_mm": 5},
        ],
    )
    result = run_fem_check("unused.step", plan, "bracket", 1.0)
    assert result["status"] == "skipped"
    assert "gmsh" in result["reason"]
    assert "fem" in result["reason"]


def test_result_always_exits_0_on_skip(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan(load=None)))
    result = subprocess.run(
        [
            sys.executable,
            FEM_CHECK,
            "unused.step",
            "--plan",
            str(plan_path),
            "--part",
            "bracket",
            "--mesh-size",
            "1.0",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "skipped"


def test_mesh_size_is_required_argument(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan(load=None)))
    result = subprocess.run(
        [sys.executable, FEM_CHECK, "unused.step", "--plan", str(plan_path), "--part", "bracket"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "mesh-size" in result.stderr


# ---- pure-function unit tests (no gmsh/skfem needed) ----


def test_failure_index_dominant_term_selected():
    # sigma_zz dominant relative to S_z
    sigma = np.diag([1.0, 1.0, 20.0])
    fi = failure_index(sigma, s_z=25.0, s_shear=20.0, s_inplane=45.0)
    assert fi == pytest.approx(20.0 / 25.0)


def test_resolve_boundary_conditions_applied_dir_overrides():
    part = {
        "load": {
            "dir": [0, 0, -1],
            "applied_dir": [0, -0.5, -1],
            "magnitude_n": 1.0,
            "applied_at": "tip",
            "grounded_at": ["root"],
        },
        "interfaces": [
            {"name": "tip", "position_mm": [10, 0, 0], "diameter_mm": 5},
            {"name": "root", "position_mm": [0, 0, 0], "diameter_mm": 5},
        ],
    }
    bc, reason = _resolve_boundary_conditions(part)
    assert reason is None
    assert bc is not None
    assert list(bc["dir"]) == [0, -0.5, -1]


def test_thickness_mismatch_warning_absent_when_close(tmp_path):
    from fem_check import _resolve_shell_thicknesses, _thickness_mismatch_warning

    plan = {"nozzle_mm": 0.4, "constraints": {"wall_min_mm": 1.2, "top_bottom_layers": 6}}
    wall_mm, topbot_mm = _resolve_shell_thicknesses(plan)  # 6 * (0.4 * 0.5) = 1.2, 0% diff
    assert _thickness_mismatch_warning(wall_mm, topbot_mm) is None


def test_thickness_mismatch_warning_present_when_divergent(tmp_path):
    from fem_check import _resolve_shell_thicknesses, _thickness_mismatch_warning

    # wall 1.2mm vs top/bottom 4 * (0.4 * 0.5) = 0.8mm -> 33% diff
    plan = {"nozzle_mm": 0.4, "constraints": {"wall_min_mm": 1.2}}
    wall_mm, topbot_mm = _resolve_shell_thicknesses(plan)
    warning = _thickness_mismatch_warning(wall_mm, topbot_mm)
    assert warning is not None
    assert warning["wall_min_mm"] == pytest.approx(1.2)
    assert warning["top_bottom_mm"] == pytest.approx(0.8)
    assert warning["pct_diff"] == pytest.approx(0.4 / 1.2, abs=1e-3)


def test_resolve_shell_thicknesses_reads_profile_motion_layer_height(tmp_path):
    from fem_check import _resolve_shell_thicknesses

    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text("{}", encoding="utf-8")
    (tmp_path / "printer_profile.json").write_text(
        json.dumps({"motion": {"layer_height_mm": 0.3}}), encoding="utf-8"
    )
    plan = {"nozzle_mm": 0.4, "constraints": {"wall_min_mm": 1.2, "top_bottom_layers": 4}}

    _, topbot_mm = _resolve_shell_thicknesses(plan, plan_path=str(plan_path))
    assert topbot_mm == pytest.approx(1.2)  # 4 * 0.3, not 4 * (0.4 * 0.5)


def test_resolve_boundary_conditions_falls_back_to_dir():
    part = {
        "load": {
            "dir": [1, 0, 0],
            "magnitude_n": 1.0,
            "applied_at": "tip",
            "grounded_at": ["root"],
        },
        "interfaces": [
            {"name": "tip", "position_mm": [10, 0, 0], "diameter_mm": 5},
            {"name": "root", "position_mm": [0, 0, 0], "diameter_mm": 5},
        ],
    }
    bc, reason = _resolve_boundary_conditions(part)
    assert reason is None
    assert bc is not None
    assert list(bc["dir"]) == [1, 0, 0]


# ---- solve-path tests: need gmsh + scikit-fem ----
#
# A module-level `pytest.importorskip` would skip collection of the WHOLE module,
# including the precondition/skip-path tests above that need no gmsh/skfem at all --
# so each solve-path test is individually marked instead, via this decorator.

_needs_fem = pytest.mark.skipif(
    importlib.util.find_spec("gmsh") is None or importlib.util.find_spec("skfem") is None,
    reason="fem dependency group not installed (uv sync --group fem)",
)


@pytest.fixture(scope="module")
def box_step(tmp_path_factory):
    """20x10x10 mm box centered at origin, authored frame X=long axis. Sized so a 4mm
    shell wall (see `_cantilever_plan`'s `wall_min_mm`) leaves a real void in every
    dimension -- the FEM advisor now solves only the wall-thickness shell, not the full
    solid, so the box must be thick enough relative to the wall for that shell to mesh
    without collapsing to near-zero thickness."""
    path = tmp_path_factory.mktemp("fem") / "box.step"
    box = cq.Workplane("XY").box(20, 10, 10)
    cq.exporters.export(box, str(path))
    return str(path)


def _cantilever_plan(load_dir, magnitude_n=5.0):
    return {
        "material": "PETG",
        "constraints": {"wall_min_mm": 4.0},
        "parts": [
            {
                "id": "bar",
                "interfaces": [
                    {
                        "type": "screw_boss",
                        "name": "fixed_end",
                        "position_mm": [-10, 0, 0],
                        "diameter_mm": 10,
                    },
                    {
                        "type": "shelf",
                        "name": "pull_end",
                        "position_mm": [10, 0, 0],
                        "diameter_mm": 10,
                    },
                ],
                "load": {
                    "dir": load_dir,
                    "magnitude_n": magnitude_n,
                    "applied_at": "pull_end",
                    "grounded_at": ["fixed_end"],
                },
            }
        ],
    }


@_needs_fem
def test_solve_path_gives_ok_status_and_sane_fields(box_step):
    result = run_fem_check(box_step, _cantilever_plan([0, 0, -1]), "bar", mesh_size=1.5)
    assert result["status"] == "ok"
    assert result["mesh"]["node_count"] > 0
    assert result["mesh"]["element_count"] > 0
    assert result["authored_frame"]["fi_max"] >= result["authored_frame"]["fi_p99"] >= 0
    assert len(result["candidates"]) >= 6  # at least the six axis-aligned candidates
    for c in result["candidates"]:
        assert c["fi_max"] >= c["fi_p99"] >= 0


@_needs_fem
def test_boundary_conditions_are_echoed(box_step):
    result = run_fem_check(box_step, _cantilever_plan([0, 0, -1]), "bar", mesh_size=1.5)
    bc = result["boundary_conditions"]
    assert bc["applied"]["name"] == "pull_end"
    assert bc["applied"]["node_count"] > 0
    assert bc["grounded"][0]["name"] == "fixed_end"
    assert bc["grounded"][0]["node_count"] > 0


@_needs_fem
def test_load_across_layers_scores_worse_than_in_plane(box_step):
    """Axial tension along X: candidates that keep X (the load/stress axis) in the
    layer plane must score a lower (better) failure index than the candidate that
    puts X along build Z (load/stress across layers)."""
    plan = _cantilever_plan([1, 0, 0], magnitude_n=20.0)
    result = run_fem_check(box_step, plan, "bar", mesh_size=1.5)
    by_normal = {tuple(c["normal"]): c["fi_p99"] for c in result["candidates"]}
    across_layers = by_normal[(1.0, 0.0, 0.0)]  # X -> build Z: load across layers
    in_plane = by_normal[(0.0, 1.0, 0.0)]  # Y -> build Z: load (X) stays in-plane
    assert across_layers > in_plane


@_needs_fem
def test_applied_dir_changes_solved_field(box_step):
    plan_a = _cantilever_plan([0, 0, -1])
    plan_b = _cantilever_plan([0, 0, -1])
    plan_b["parts"][0]["load"]["applied_dir"] = [0, -1, -1]

    result_a = run_fem_check(box_step, plan_a, "bar", mesh_size=1.5)
    result_b = run_fem_check(box_step, plan_b, "bar", mesh_size=1.5)
    dir_a = result_a["boundary_conditions"]["applied_dir"]
    dir_b = result_b["boundary_conditions"]["applied_dir"]
    assert dir_a != dir_b
    assert result_a["authored_frame"]["fi_max"] != result_b["authored_frame"]["fi_max"]


@_needs_fem
def test_mesh_independence_of_fi_p99(box_step):
    coarse = run_fem_check(box_step, _cantilever_plan([0, 0, -1]), "bar", mesh_size=2.0)
    fine = run_fem_check(box_step, _cantilever_plan([0, 0, -1]), "bar", mesh_size=1.0)
    assert coarse["status"] == "ok" and fine["status"] == "ok"
    assert coarse["mesh"]["mesh_size_mm"] == 2.0
    assert fine["mesh"]["mesh_size_mm"] == 1.0
    assert coarse["mesh"]["element_count"] != fine["mesh"]["element_count"]
    # fi_p99 (used downstream) should stay within the same order of magnitude across
    # a 2x mesh refinement even though fi_max (sensitive to local BC-patch artifacts)
    # may move more.
    ratio = fine["authored_frame"]["fi_p99"] / coarse["authored_frame"]["fi_p99"]
    assert 0.3 < ratio < 3.0


@_needs_fem
def test_concentration_ratio_and_hint_present(box_step):
    result = run_fem_check(box_step, _cantilever_plan([0, 0, -1]), "bar", mesh_size=1.5)
    assert result["concentration_ratio"] >= 1.0
    assert result["hint"]
    if result["concentration_ratio"] > result["concentration_threshold"]:
        assert "fillet" in result["hint"] or "chamfer" in result["hint"]
    else:
        assert "thicken" in result["hint"] or "orient" in result["hint"]
