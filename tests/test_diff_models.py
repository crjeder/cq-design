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


def _two_cubes(tmp_path, second_at):
    base = _box((40, 20, 20))
    parts = [base, _box((10, 10, 10), (0, 0, 15))]
    if second_at:
        parts.append(_box((6, 6, 6), second_at))
    return (
        _save(tmp_path, "a.stl", base),
        _save(tmp_path, "b.stl", trimesh.util.concatenate(parts)),
    )


REGION = (-10, -10, 10, 10, 10, 30)


def test_localized_inside_region(tmp_path):
    a, b = _two_cubes(tmp_path, None)
    r = diff_models(a, b, region=REGION, expect_volume=(900, 1100))
    assert r["localized"] and r["outside_volume"] < 1e-3
    assert r["volume_in_range"] and abs(r["volume_delta"] - 1000) < 1e-3
    assert r["changed_bbox"] == [[-5, -5, 10], [5, 5, 20]]


def test_collateral_outside_region(tmp_path):
    a, b = _two_cubes(tmp_path, (15, 0, 13))
    r = diff_models(a, b, region=REGION)
    assert not r["localized"] and abs(r["outside_volume"] - 216) < 1e-3


def test_volume_out_of_range(tmp_path):
    a, b = _two_cubes(tmp_path, None)
    assert diff_models(a, b, expect_volume=(2000, 3000))["volume_in_range"] is False


def test_checks_absent_are_null(tmp_path):
    a, b = _two_cubes(tmp_path, None)
    r = diff_models(a, b)
    assert r["localized"] is None and r["volume_in_range"] is None and r["region_fraction"] is None


def test_region_equal_to_bbox(tmp_path):
    a, b = _two_cubes(tmp_path, None)
    assert abs(diff_models(a, b, region=(-20, -10, -10, 20, 10, 10))["region_fraction"] - 1) < 1e-9
