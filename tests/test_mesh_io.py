import numpy as np
import pytest
import trimesh

import mesh_io


def _downward_tri(gamma_deg):
    """A single downward-facing triangle (area 0.5) whose overhang angle from
    horizontal is 90 - gamma_deg. Smaller gamma => steeper (nearer-horizontal)."""
    g = np.radians(gamma_deg)
    verts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, -np.cos(g), -np.sin(g)]])
    return trimesh.Trimesh(vertices=verts, faces=[[0, 1, 2]], process=False)


def test_support_cost_weights_steeper_overhangs_more():
    # Equal area; the steeper (near-horizontal, angle 80) face costs more than the
    # one just past the limit (angle 50).
    steep = mesh_io.support_cost(_downward_tri(10.0), 45.0, 2.0)  # angle 80
    shallow = mesh_io.support_cost(_downward_tri(40.0), 45.0, 2.0)  # angle 50
    assert steep > shallow > 0.0


def test_support_cost_zero_at_or_under_limit():
    # angle 40 <= 45 limit -> not an unsupported overhang -> zero cost.
    assert mesh_io.support_cost(_downward_tri(50.0), 45.0, 2.0) == 0.0


def test_support_cost_excludes_masked_faces():
    tri = _downward_tri(10.0)
    assert mesh_io.support_cost(tri, 45.0, 2.0) > 0.0
    excluded = np.array([True])
    assert mesh_io.support_cost(tri, 45.0, 2.0, exclude_mask=excluded) == 0.0


def test_load_mesh_valid(tmp_stl):
    tm = mesh_io.load_mesh(str(tmp_stl))
    assert len(tm.vertices) > 0
    assert len(tm.faces) > 0
    assert tm.is_watertight


def test_load_mesh_missing_file(tmp_path):
    with pytest.raises(ValueError, match="Failed to load STL"):
        mesh_io.load_mesh(str(tmp_path / "nope.stl"))


def test_load_mesh_empty_file(tmp_path):
    empty = tmp_path / "empty.stl"
    empty.write_bytes(b"")
    with pytest.raises(ValueError):
        mesh_io.load_mesh(str(empty))


def test_load_mesh_no_pyrender_import():
    """mesh_io must not pull in pyrender (it's the whole point of the split)."""
    assert "pyrender" not in dir(mesh_io), "mesh_io should not reference pyrender"
