import trimesh

from diff_models import diff_models


def _save(tmp_path, name, mesh):
    p = str(tmp_path / name)
    mesh.export(p)
    return p


def _box(size, at=(0, 0, 0)):
    return trimesh.creation.box(
        extents=size, transform=trimesh.transformations.translation_matrix(at)
    )


def test_added_cube(tmp_path):
    a = _save(tmp_path, "a.stl", _box((20, 20, 20)))
    # cube fully outside A, touching nothing shared
    b = _save(
        tmp_path,
        "b.stl",
        trimesh.util.concatenate([_box((20, 20, 20)), _box((10, 10, 10), (30, 0, 0))]),
    )
    png = str(tmp_path / "d.png")
    r = diff_models(a, b, png)
    assert r["success"] and not r["identical"]
    assert abs(r["only_b_volume"] - 1000) < 1e-3 and r["only_a_volume"] == 0
    assert (tmp_path / "d.png").exists() and r["png"] == png


def test_identical(tmp_path):
    a = _save(tmp_path, "a.stl", _box((5, 5, 5)))
    b = _save(tmp_path, "b.stl", _box((5, 5, 5)))
    r = diff_models(a, b)
    assert r["success"] and r["identical"] and r["only_a_volume"] == 0 == r["only_b_volume"]


def test_not_watertight(tmp_path):
    open_mesh = _box((5, 5, 5))
    open_mesh.faces = open_mesh.faces[:-2]
    a = _save(tmp_path, "a.stl", open_mesh)
    b = _save(tmp_path, "b.stl", _box((5, 5, 5)))
    r = diff_models(a, b)
    assert not r["success"] and r["errors"][0]["type"] == "not_watertight"
