"""Thin-interface detection: local thickness with XY/Z direction classification.

Geometry-level tests build meshes directly with trimesh (fast, no CadQuery);
the wrapper-contract test runs a real CadQuery script through the JSON wrapper.
"""

import json
import subprocess
import sys

import numpy as np
import trimesh

import measure_stl


def _box(extents, translate=(0, 0, 0)):
    return trimesh.creation.box(
        extents=extents,
        transform=trimesh.transformations.translation_matrix(translate),
    )


def _write(mesh, path):
    mesh.export(str(path))
    return str(path)


def test_thin_vertical_fin_detected_as_xy(tmp_path):
    """A 2 mm vertical fin beside a 20 mm block is found at ~2 mm, thin-in-XY,
    even though bbox/volume are dominated by the block."""
    block = _box([20, 20, 20])
    fin = _box([2, 10, 20], translate=(0, 15, 0))  # thin in X, stands vertically
    stl = _write(trimesh.util.concatenate([block, fin]), tmp_path / "fin.stl")

    regions = measure_stl.measure(stl, thin_max_mm=3.0)["thin_regions"]
    xy = [r for r in regions if r["orientation"] == "xy"]
    assert xy, "expected an XY-thin region for the fin"
    assert any(1.5 <= r["thickness_mm"] <= 2.5 for r in xy)


def test_thin_wall_detected_above_sample_cap(tmp_path):
    """Regression: a thin wall must still be found when the mesh has more faces than
    the ray-cast sample cap. Measuring the same dense mesh with a large cap (sample
    everything) and a tiny cap (high-stride subsampling) must give the same finding --
    previously the strided samples fragmented into dropped singletons and the wall
    silently vanished."""
    block = _box([20, 20, 20])
    fin = _box([2, 10, 20], translate=(0, 15, 0))  # 2 mm thin in X
    mesh = trimesh.util.concatenate([block, fin])
    for _ in range(3):  # 24 -> 1536 faces, well past the tiny cap below
        mesh = mesh.subdivide()
    stl = _write(mesh, tmp_path / "fin_dense.stl")

    full = measure_stl.measure(stl, thin_max_mm=3.0, max_samples=100_000)["thin_regions"]
    capped = measure_stl.measure(stl, thin_max_mm=3.0, max_samples=100)["thin_regions"]

    full_xy = [r for r in full if r["orientation"] == "xy"]
    capped_xy = [r for r in capped if r["orientation"] == "xy"]
    assert full_xy, "fin not found even when every face is sampled"
    assert capped_xy, "fin lost under high-stride subsampling (fragmentation regression)"
    # Stable across density: both report the wall at ~2 mm.
    assert any(1.5 <= r["thickness_mm"] <= 2.5 for r in full_xy)
    assert any(1.5 <= r["thickness_mm"] <= 2.5 for r in capped_xy)


def test_uniform_thick_mesh_above_cap_reports_nothing(tmp_path):
    """The density-robust grouping must not manufacture regions from the transparent
    unsampled faces: a uniformly thick dense mesh still reports no thin regions."""
    cube = _box([20, 20, 20])
    for _ in range(3):  # 12 -> 768 faces
        cube = cube.subdivide()
    stl = _write(cube, tmp_path / "cube_dense.stl")

    regions = measure_stl.measure(stl, thin_max_mm=3.0, max_samples=100)["thin_regions"]
    assert regions == [], f"expected no thin regions on a 20 mm-thick cube; got {regions}"


def test_flat_slab_thin_in_z_not_xy(tmp_path):
    """A 1 mm plate lying flat is thin only along Z and must classify as 'z'."""
    stl = _write(_box([40, 40, 1]), tmp_path / "slab.stl")

    regions = measure_stl.measure(stl, thin_max_mm=3.0)["thin_regions"]
    assert regions, "expected the slab to register as a thin region"
    assert all(r["orientation"] == "z" for r in regions)


def test_nearest_feature_null_when_far():
    """A point beyond the snap radius from all features returns None."""
    import numpy as np

    flat_faces = [{"center_xy_mm": [0.0, 0.0], "z_mm": 0.0}]
    cylinders = [{"type": "boss", "center_xy_mm": [0.0, 0.0], "z_range_mm": [0, 10]}]
    far_point = np.array([100.0, 0.0, 0.0])
    assert measure_stl._nearest_feature(far_point, flat_faces, cylinders, 15.0) is None


def test_nearest_feature_snaps_when_near():
    """A point within the snap radius returns the nearest feature label."""
    import numpy as np

    flat_faces = [{"center_xy_mm": [0.0, 0.0], "z_mm": 5.0}]
    near_point = np.array([1.0, 0.0, 5.0])
    nf = measure_stl._nearest_feature(near_point, flat_faces, [], 15.0)
    assert nf is not None
    assert nf["feature"].startswith("flat_face")
    assert nf["distance_mm"] == 1.0


def test_wrapper_emits_thin_interface_error_and_geometry(tmp_path, skill_src):
    """run_cadquery_model.py emits a typed thin_interface error with the full
    payload and lists thin_regions in the geometry block."""
    script = tmp_path / "finmodel.py"
    script.write_text(
        "import cadquery as cq\n"
        "result = (cq.Workplane('XY').box(20, 20, 20)"
        ".union(cq.Workplane('XY').transformed(offset=(0, 15, 0)).box(2, 10, 20)))\n"
        "cq.exporters.export(result, 'finmodel.stl',"
        " tolerance=0.01, angularTolerance=0.1)\n"
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(skill_src / "run_cadquery_model.py"),
            str(script),
            "--wall-min",
            "3.0",
            "--line-width",
            "0.42",
        ],
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout)

    thin = [e for e in data["errors"] if e["type"] == "thin_interface"]
    assert thin, f"expected a thin_interface error; got {data['errors']}"
    e = thin[0]
    for key in (
        "thickness_mm",
        "equiv_diameter_mm",
        "min_mm",
        "orientation",
        "location_xyz_mm",
        "thin_direction",
        "nearest_feature",
        "hint",
    ):
        assert key in e, f"missing {key} in thin_interface error"
    assert e["orientation"] == "xy"
    assert "thin_regions" in data["geometry"]


def test_prefilter_matches_unfiltered_cast():
    """The facing/in-front pre-filter must not change per-face thickness."""
    mesh = trimesh.util.concatenate([_box([20, 20, 20]), _box([2, 10, 20], (0, 25, 0))])
    mesh = mesh.subdivide().subdivide()
    idx = np.arange(len(mesh.faces))
    fast = measure_stl._sampled_thickness(mesh, idx, 1e-3, prefilter=True)
    ref = measure_stl._sampled_thickness(mesh, idx, 1e-3, prefilter=False)
    assert np.allclose(fast, ref, equal_nan=True)
